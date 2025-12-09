import json
import boto3
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

# Environment variables
S3_RAW_BUCKET = os.environ.get('S3_RAW_AUDIT_BUCKET')
S3_PROCESSED_BUCKET = os.environ.get('S3_PROCESSED_BUCKET')
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
EVENT_VERSION = os.environ.get('EVENT_VERSION', '1.0')

# Fields to strip from payload
FIELDS_TO_STRIP = {
    'products': ['created_at', 'updated_at', 'archived_at'],
    'product_variants': [
        'image_url', 'stock_quantity', 'is_default', 'stockStatus',
        'lab_test_codes_id', 'service_product_id', 'cpr_price', 'archived_at'
    ],
    'categories': ['user_id', 'created_at', 'last_modified', 'image']
}


def calculate_payload_hash(payload: Dict[str, Any]) -> str:
    """
    Calculate SHA-256 hash of the payload for idempotency checking.
    
    Args:
        payload: The webhook payload dictionary
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()


def strip_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively strip specified fields from the payload.
    Creates a deep copy to avoid modifying the original.
    
    Args:
        payload: The original webhook payload
        
    Returns:
        Modified payload with specified fields removed
    """
    def deep_copy_and_strip(obj: Any, fields_to_remove: Dict[str, list], context: str = 'root') -> Any:
        """Recursively copy and strip fields from nested structures.
        
        Args:
            obj: The object to process
            fields_to_remove: Dictionary mapping context to fields to remove
            context: Current context ('products', 'product_variants', 'categories', etc.)
        """
        if isinstance(obj, dict):
            result = {}
            # Determine current context for field stripping
            current_context = context
            if 'product_variants' in obj or (context == 'products' and any('product_id' in item for item in (obj.values() if isinstance(obj, dict) else []))):
                # We're in a product_variants array item
                pass
            elif context == 'products' and 'id' in obj and 'name' in obj and 'is_featured' in obj:
                # This looks like a category object
                current_context = 'categories'
            
            for key, value in obj.items():
                # Check if this key should be stripped based on current context
                should_strip = False
                if current_context in fields_to_remove:
                    if key in fields_to_remove[current_context]:
                        should_strip = True
                
                if not should_strip:
                    # Determine next context for nested structures
                    next_context = current_context
                    if key == 'product_variants':
                        next_context = 'product_variants'
                    elif key == 'categories':
                        next_context = 'categories'
                    elif key == 'products':
                        next_context = 'products'
                    
                    # Recursively process nested structures
                    if isinstance(value, (dict, list)):
                        result[key] = deep_copy_and_strip(value, fields_to_remove, next_context)
                    else:
                        result[key] = value
            return result
        elif isinstance(obj, list):
            # For lists, determine context from parent
            if context == 'products':
                # Check if this is product_variants or categories array
                if obj and isinstance(obj[0], dict):
                    if 'product_id' in obj[0]:
                        # This is product_variants
                        return [deep_copy_and_strip(item, fields_to_remove, 'product_variants') for item in obj]
                    elif 'is_featured' in obj[0]:
                        # This is categories
                        return [deep_copy_and_strip(item, fields_to_remove, 'categories') for item in obj]
            return [deep_copy_and_strip(item, fields_to_remove, context) for item in obj]
        else:
            return obj
    
    return deep_copy_and_strip(payload, FIELDS_TO_STRIP, 'root')


def get_store_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract store_id from payload.
    Checks multiple locations: top-level, products.store_id, or store_id as UUID.
    
    Args:
        payload: The webhook payload
        
    Returns:
        store_id as string, or None if not found
    """
    # Check top-level store_id (for store events)
    if 'store_id' in payload:
        store_id = payload['store_id']
        if isinstance(store_id, str):
            return store_id
        elif isinstance(store_id, dict) and 'id' in store_id:
            return store_id['id']
    
    # Check products.store_id (for product events)
    if 'products' in payload and isinstance(payload['products'], dict):
        products = payload['products']
        if 'store_id' in products:
            store_id = products['store_id']
            if isinstance(store_id, str):
                return store_id
    
    return None


def get_product_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract product_id from payload.
    Checks products.product_id or products.id.
    
    Args:
        payload: The webhook payload
        
    Returns:
        product_id as string, or None if not found
    """
    if 'products' in payload and isinstance(payload['products'], dict):
        products = payload['products']
        # Check for product_id first (new schema)
        if 'product_id' in products:
            return str(products['product_id'])
        # Fallback to id (original schema)
        elif 'id' in products:
            return str(products['id'])
    
    return None


def get_store_domain(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract store domain from payload.
    Checks for store_domain, store.domain, or store_id.domain.
    
    Args:
        payload: The webhook payload
        
    Returns:
        store_domain as string, or None if not found
    """
    # Check top-level store_domain
    if 'store_domain' in payload:
        return str(payload['store_domain'])
    
    # Check store_id object for domain
    if 'store_id' in payload:
        store_id = payload['store_id']
        if isinstance(store_id, dict):
            if 'domain' in store_id:
                return str(store_id['domain'])
            elif 'store_domain' in store_id:
                return str(store_id['store_domain'])
    
    # Check products.store_domain (for product events)
    if 'products' in payload and isinstance(payload['products'], dict):
        products = payload['products']
        if 'store_domain' in products:
            return str(products['store_domain'])
    
    return None


def get_company_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract company_id from payload.
    For now, company_id is the same as store_id (multitenancy by store).
    Can be extended to support separate company_id field.
    
    Args:
        payload: The webhook payload
        
    Returns:
        company_id as string (store_id), or None if not found
    """
    # For now, company_id = store_id (multitenancy by store)
    # Can be extended if separate company_id field is added
    return get_store_id(payload)


def check_store_exists(store_id: str) -> bool:
    """
    Check if a store exists in our system by looking for store metadata in S3.
    
    Args:
        store_id: Store identifier
        
    Returns:
        True if store exists, False otherwise
    """
    # Check if store metadata exists in S3
    # Look for any store_create event with this store_id
    try:
        # List objects with prefix to check if store has been created
        # We'll check if there's a store_create event for this store_id
        response = s3_client.list_objects_v2(
            Bucket=S3_RAW_BUCKET,
            Prefix=f"{store_id}/store_create/",
            MaxKeys=1
        )
        return 'Contents' in response and len(response['Contents']) > 0
    except Exception as e:
        logger.warning(f"Error checking if store exists: {str(e)}")
        # If we can't check, assume it doesn't exist to be safe
        return False


def check_product_exists(product_id: str) -> bool:
    """
    Check if a product exists in our system by checking the master catalog.
    
    Args:
        product_id: Product identifier
        
    Returns:
        True if product exists, False otherwise
    """
    # Check if product exists in master catalog
    master_key = f"master/products/{product_id}.json"
    try:
        s3_client.head_object(Bucket=S3_PROCESSED_BUCKET, Key=master_key)
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            logger.warning(f"Error checking if product exists: {str(e)}")
            # If we can't check, assume it doesn't exist to be safe
            return False


def create_store_if_not_exists(store_id: str, payload: Dict[str, Any], event_id: str) -> Optional[str]:
    """
    Create store metadata if store doesn't exist in our system.
    
    Args:
        store_id: Store identifier
        payload: The webhook payload
        event_id: Event identifier
        
    Returns:
        S3 key where store metadata was created, or None if store already exists
    """
    if check_store_exists(store_id):
        logger.info(f"Store {store_id} already exists, skipping creation")
        return None
    
    logger.info(f"Creating new store: {store_id}")
    
    # Extract store domain
    store_domain = get_store_domain(payload)
    
    # Create store metadata
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    metadata = {
        "metadataAttributes": {
            "store": store_domain or store_id,
            "store_id": store_id,
            "created_at": now.isoformat() + 'Z',
            "created_by_event": event_id
        }
    }
    
    # Store metadata in the same location as store_create events
    metadata_s3_key = f"{store_id}/store_create/{year}/{month}/{day}/{event_id}.metadata.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_RAW_BUCKET,
            Key=metadata_s3_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Created store metadata: {metadata_s3_key}")
        return metadata_s3_key
    except Exception as e:
        logger.error(f"Error creating store metadata: {str(e)}")
        raise


def create_product_if_not_exists(product_id: str, payload: Dict[str, Any]) -> Optional[str]:
    """
    Create product in master catalog if product doesn't exist in our system.
    
    Args:
        product_id: Product identifier
        payload: The webhook payload
        
    Returns:
        S3 key where product was created, or None if product already exists
    """
    if check_product_exists(product_id):
        logger.info(f"Product {product_id} already exists, skipping creation")
        return None
    
    logger.info(f"Creating new product: {product_id}")
    
    # Store product to master catalog
    master_key = f"master/products/{product_id}.json"
    
    try:
        # Use the payload's products object if available, otherwise create minimal structure
        if 'products' in payload and isinstance(payload['products'], dict):
            product_data = payload['products'].copy()
        else:
            # Create minimal product structure
            product_data = {
                "product_id": product_id,
                "created_at": datetime.utcnow().isoformat() + 'Z'
            }
        
        s3_client.put_object(
            Bucket=S3_PROCESSED_BUCKET,
            Key=master_key,
            Body=json.dumps({"products": product_data}, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Created product in master catalog: {master_key}")
        return master_key
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise


def detect_event_type(payload: Dict[str, Any]) -> str:
    """
    Determine event type based on payload structure.
    First checks for explicit event_type field, then falls back to detection.
    
    Args:
        payload: The webhook payload
        
    Returns:
        Event type string (product_create, product_update, product_delete, etc.)
    """
    # First, check for explicit event_type field (new simplified payloads)
    if 'event_type' in payload:
        event_type = payload['event_type']
        if isinstance(event_type, str) and event_type:
            # Normalize event type names
            event_type_map = {
                'product_update': 'product_update',
                'product_deletion': 'product_delete',
                'new_product': 'product_create',
                'new_store': 'store_create',
                'deleted_store': 'store_delete',
                'updated_store': 'store_update'
            }
            return event_type_map.get(event_type, event_type)
    
    # Fallback to detection logic (for backward compatibility with original payloads)
    # Check for products in payload
    if 'products' in payload:
        products = payload['products']
        
        # Check if this is a deletion (archived_at present and not null)
        if isinstance(products, dict) and products.get('archived_at'):
            return 'product_delete'
        
        # Check if this is an update (has id and updated_at)
        if isinstance(products, dict) and products.get('id') or products.get('product_id'):
            # Could be create or update - check if we have more context
            # For now, assume update if id exists
            return 'product_update'
        
        # Otherwise, likely a create
        return 'product_create'
    
    # Check for store-related events (if store_id is present)
    if 'store_id' in payload:
        store_id = payload['store_id']
        if store_id and isinstance(store_id, dict):
            if store_id.get('archived_at'):
                return 'store_delete'
            elif store_id.get('id'):
                return 'store_update'
            else:
                return 'store_create'
        elif isinstance(store_id, str):
            # Just store_id as UUID - need to determine from context
            # Default to store_update if we can't tell
            return 'store_update'
    
    # Default to unknown if we can't determine
    return 'unknown'


def get_routing_target(event_type: str) -> str:
    """
    Determine routing target based on event type.
    Placeholder implementation for now.
    
    Args:
        event_type: The detected event type
        
    Returns:
        Routing target identifier
    """
    routing_map = {
        'product_create': 'product-service',
        'product_update': 'product-service',
        'product_delete': 'product-service',
        'store_create': 'store-service',
        'store_update': 'store-service',
        'store_delete': 'store-service',
        'unknown': 'default-handler'
    }
    return routing_map.get(event_type, 'default-handler')


def check_idempotency(payload_hash: str, table) -> Optional[Dict[str, Any]]:
    """
    Check if this event has already been processed.
    
    Args:
        payload_hash: SHA-256 hash of the payload
        table: DynamoDB table resource
        
    Returns:
        Existing event record if found, None otherwise
    """
    try:
        response = table.query(
            KeyConditionExpression='payload_hash = :hash',
            ExpressionAttributeValues={':hash': payload_hash},
            Limit=1,
            ScanIndexForward=False  # Get most recent first
        )
        
        if response.get('Items'):
            return response['Items'][0]
        return None
    except Exception as e:
        logger.error(f"Error checking idempotency: {str(e)}")
        # Don't fail on idempotency check errors - allow processing to continue
        return None


def store_raw_payload(payload: Dict[str, Any], event_type: str, event_id: str, store_id: Optional[str] = None) -> str:
    """
    Store raw payload to S3 with date-based partitioning including store_id.
    
    Args:
        payload: The raw webhook payload
        event_type: The detected event type
        event_id: Unique event identifier
        store_id: Store identifier (optional, extracted if not provided)
        
    Returns:
        S3 key where the payload was stored
    """
    if store_id is None:
        store_id = get_store_id(payload) or 'unknown'
    
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # S3 key: {store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json
    s3_key = f"{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_RAW_BUCKET,
            Key=s3_key,
            Body=json.dumps(payload, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Stored raw payload to S3: {s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"Error storing raw payload to S3: {str(e)}")
        raise


def store_store_metadata(
    payload: Dict[str, Any],
    event_type: str,
    event_id: str,
    store_id: str,
    product_id: Optional[str] = None
) -> Optional[str]:
    """
    Store metadata file for store creation events.
    Stores metadata in the same folder as the main event file.
    
    Args:
        payload: The raw webhook payload
        event_type: The detected event type
        event_id: Unique event identifier
        store_id: Store identifier
        product_id: Product identifier (optional)
        
    Returns:
        S3 key where the metadata was stored, or None if not a store creation event
    """
    # Only store metadata for store creation events
    if event_type != 'store_create':
        return None
    
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # Extract store domain
    store_domain = get_store_domain(payload)
    
    # Build metadata structure matching our schema
    metadata = {
        "metadataAttributes": {
            "store": store_domain or store_id,
            "store_id": store_id
        }
    }
    
    # Add product_id if available
    if product_id:
        metadata["metadataAttributes"]["product_id"] = product_id
    
    # S3 key: {store_id}/{event_type}/{year}/{month}/{day}/{event_id}.metadata.json
    metadata_s3_key = f"{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.metadata.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_RAW_BUCKET,
            Key=metadata_s3_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Stored store metadata to S3: {metadata_s3_key}")
        return metadata_s3_key
    except Exception as e:
        logger.error(f"Error storing store metadata to S3: {str(e)}")
        raise


def store_processed_payload(payload: Dict[str, Any], event_type: str, event_id: str, store_id: Optional[str] = None) -> str:
    """
    Store processed/stripped payload to S3 with date-based partitioning including store_id.
    
    Args:
        payload: The processed/stripped webhook payload
        event_type: The detected event type
        event_id: Unique event identifier
        store_id: Store identifier (optional, extracted if not provided)
        
    Returns:
        S3 key where the processed payload was stored
    """
    if store_id is None:
        store_id = get_store_id(payload) or 'unknown'
    
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # S3 key: {store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json
    s3_key = f"{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_PROCESSED_BUCKET,
            Key=s3_key,
            Body=json.dumps(payload, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Stored processed payload to S3: {s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"Error storing processed payload to S3: {str(e)}")
        raise


def store_to_master_catalog(payload: Dict[str, Any], product_id: str) -> str:
    """
    Store product to master catalog in S3.
    
    Args:
        payload: The product payload (full or processed)
        product_id: Product identifier
        
    Returns:
        S3 key where the product was stored
    """
    s3_key = f"master/products/{product_id}.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_PROCESSED_BUCKET,
            Key=s3_key,
            Body=json.dumps(payload, indent=2),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        logger.info(f"Stored product to master catalog: {s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"Error storing to master catalog: {str(e)}")
        raise


def copy_to_store_catalog(product_id: str, store_id: str, modifications: Dict[str, Any]) -> str:
    """
    Copy product from master catalog to store-specific catalog with modifications.
    
    Args:
        product_id: Product identifier
        store_id: Store identifier
        modifications: Store-specific modifications (e.g., price changes)
        
    Returns:
        S3 key where the store product was stored
    """
    # Get product from master catalog
    master_key = f"master/products/{product_id}.json"
    
    try:
        # Fetch from master catalog
        response = s3_client.get_object(Bucket=S3_PROCESSED_BUCKET, Key=master_key)
        master_product = json.loads(response['Body'].read().decode('utf-8'))
        
        # Apply modifications
        if 'products' in master_product and isinstance(master_product['products'], dict):
            store_product = master_product.copy()
            store_product['products'] = master_product['products'].copy()
            
            # Apply price modifications to product_variants
            if 'product_variants' in store_product['products'] and modifications.get('price'):
                for variant in store_product['products']['product_variants']:
                    if isinstance(variant, dict):
                        variant['price'] = modifications['price']
            
            # Update store_id
            store_product['products']['store_id'] = store_id
            
            # Store to store catalog
            store_key = f"stores/{store_id}/products/{product_id}.json"
            s3_client.put_object(
                Bucket=S3_PROCESSED_BUCKET,
                Key=store_key,
                Body=json.dumps(store_product, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            logger.info(f"Copied product to store catalog: {store_key}")
            return store_key
        else:
            raise ValueError("Invalid master product structure")
            
    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"Master product not found: {master_key}, creating from payload")
        # If master doesn't exist, create it from current payload
        # This handles cases where webhook creates product directly
        return None
    except Exception as e:
        logger.error(f"Error copying to store catalog: {str(e)}")
        raise


def delete_from_store_catalog(product_id: str, store_id: str) -> None:
    """
    Delete product from store-specific catalog.
    
    Args:
        product_id: Product identifier
        store_id: Store identifier
    """
    store_key = f"stores/{store_id}/products/{product_id}.json"
    
    try:
        s3_client.delete_object(
            Bucket=S3_PROCESSED_BUCKET,
            Key=store_key
        )
        logger.info(f"Deleted product from store catalog: {store_key}")
    except Exception as e:
        logger.error(f"Error deleting from store catalog: {str(e)}")
        raise


def trigger_kb_refresh(store_id: str) -> None:
    """
    Trigger Knowledge Base refresh for a specific store.
    Uses SNS topic if configured, otherwise logs the event.
    
    Args:
        store_id: Store identifier
    """
    kb_refresh_topic = os.environ.get('KB_REFRESH_SNS_TOPIC')
    
    if kb_refresh_topic:
        try:
            sns_client.publish(
                TopicArn=kb_refresh_topic,
                Subject=f'KB Refresh Request: Store {store_id}',
                Message=json.dumps({
                    'store_id': store_id,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'trigger': 'webhook_processor'
                })
            )
            logger.info(f"Triggered KB refresh for store: {store_id}")
        except Exception as e:
            logger.error(f"Error triggering KB refresh: {str(e)}")
            # Don't fail the entire process if KB refresh fails
    else:
        logger.info(f"KB refresh requested for store: {store_id} (SNS topic not configured)")


def register_event(
    payload_hash: str,
    event_id: str,
    event_type: str,
    s3_key: str,
    routing_target: str,
    table,
    store_id: Optional[str] = None
) -> None:
    """
    Register event in DynamoDB event registry.
    
    Args:
        payload_hash: SHA-256 hash of the payload
        event_id: Unique event identifier
        event_type: The detected event type
        s3_key: S3 key where raw payload is stored
        routing_target: Determined routing target
        table: DynamoDB table resource
        store_id: Store identifier (optional)
    """
    now = datetime.utcnow()
    processing_timestamp = now.isoformat() + 'Z'
    
    # TTL: 7 years from now (in seconds)
    ttl = int((now.timestamp() + (7 * 365 * 24 * 60 * 60)))
    
    try:
        item = {
            'payload_hash': payload_hash,
            'processing_timestamp': processing_timestamp,
            'event_id': event_id,
            'event_type': event_type,
            's3_key': s3_key,
            'status': 'processed',
            'routing_target': routing_target,
            'ttl': ttl
        }
        
        # Add store_id if available
        if store_id:
            item['store_id'] = store_id
        
        table.put_item(Item=item)
        logger.info(f"Registered event in DynamoDB: {event_id}")
    except Exception as e:
        logger.error(f"Error registering event in DynamoDB: {str(e)}")
        raise


def enrich_payload(payload: Dict[str, Any], payload_hash: str, event_type: str) -> Dict[str, Any]:
    """
    Enrich payload with metadata.
    
    Args:
        payload: The processed payload
        payload_hash: SHA-256 hash of the original payload
        event_type: The detected event type
        
    Returns:
        Enriched payload with metadata
    """
    now = datetime.utcnow()
    
    enriched = payload.copy()
    enriched['_metadata'] = {
        'processing_timestamp': now.isoformat() + 'Z',
        'payload_hash': payload_hash,
        'event_version': EVENT_VERSION,
        'event_type': event_type
    }
    
    return enriched


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for processing webhook events.
    
    Args:
        event: EventBridge event containing webhook payload
        context: Lambda context
        
    Returns:
        Response dictionary with status and details
    """
    try:
        # Extract payload from EventBridge event
        # EventBridge format: event['detail'] contains the actual payload
        if 'detail' in event:
            raw_payload = event['detail']
        elif 'body' in event:
            # Handle direct invocation or API Gateway format
            if isinstance(event['body'], str):
                raw_payload = json.loads(event['body'])
            else:
                raw_payload = event['body']
        else:
            raw_payload = event
        
        logger.info(f"Received webhook event: {json.dumps(raw_payload)[:200]}...")
        
        # Calculate payload hash for idempotency
        payload_hash = calculate_payload_hash(raw_payload)
        logger.info(f"Payload hash: {payload_hash}")
        
        # Get DynamoDB table
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        
        # Check for duplicate events
        existing_event = check_idempotency(payload_hash, table)
        if existing_event:
            logger.info(f"Duplicate event detected. Already processed at {existing_event.get('processing_timestamp')}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'duplicate',
                    'message': 'Event already processed',
                    'event_id': existing_event.get('event_id'),
                    'original_processing_timestamp': existing_event.get('processing_timestamp')
                })
            }
        
        # Generate event ID (use hash as base, add timestamp for uniqueness)
        now = datetime.utcnow()
        event_id = f"{payload_hash[:16]}-{int(now.timestamp())}"
        
        # Detect event type
        event_type = detect_event_type(raw_payload)
        
        # Extract identifiers
        store_id = get_store_id(raw_payload)
        product_id = get_product_id(raw_payload)
        
        # Create store if it doesn't exist (for any event with a store_id)
        if store_id:
            try:
                store_metadata_key = create_store_if_not_exists(store_id, raw_payload, event_id)
                if store_metadata_key:
                    logger.info(f"Created new store: {store_id}")
            except Exception as e:
                logger.warning(f"Failed to create store if not exists: {str(e)}")
                # Continue processing even if store creation fails
        
        # Create product if it doesn't exist (for product events)
        if product_id and event_type in ['product_create', 'product_update', 'product_delete']:
            try:
                product_master_key = create_product_if_not_exists(product_id, raw_payload)
                if product_master_key:
                    logger.info(f"Created new product: {product_id}")
            except Exception as e:
                logger.warning(f"Failed to create product if not exists: {str(e)}")
                # Continue processing even if product creation fails
        
        logger.info(f"Detected event type: {event_type}, store_id: {store_id}, product_id: {product_id}")
        
        # Store raw payload to S3 (immutable audit trail)
        raw_s3_key = store_raw_payload(raw_payload, event_type, event_id, store_id)
        
        # Store metadata for store creation events
        metadata_s3_key = None
        if event_type == 'store_create':
            try:
                metadata_s3_key = store_store_metadata(
                    raw_payload,
                    event_type,
                    event_id,
                    store_id,
                    product_id
                )
                logger.info(f"Stored store metadata: {metadata_s3_key}")
            except Exception as e:
                logger.warning(f"Failed to store store metadata: {str(e)}")
                # Continue processing even if metadata storage fails
        
        # Handle master and store catalog management based on event type
        master_catalog_key = None
        store_catalog_key = None
        
        if event_type in ['product_create', 'product_update'] and product_id:
            # Store/update in master catalog
            try:
                master_catalog_key = store_to_master_catalog(raw_payload, product_id)
                logger.info(f"Stored to master catalog: {master_catalog_key}")
            except Exception as e:
                logger.warning(f"Failed to store to master catalog: {str(e)}")
                # Continue processing even if master catalog fails
        
        if event_type == 'product_create' and product_id and store_id:
            # Copy product from master to store catalog with modifications
            try:
                modifications = {}
                # Extract price modifications from product_variants if present
                if 'products' in raw_payload and 'product_variants' in raw_payload['products']:
                    variants = raw_payload['products']['product_variants']
                    if variants and isinstance(variants, list) and len(variants) > 0:
                        if 'price' in variants[0]:
                            modifications['price'] = variants[0]['price']
                
                store_catalog_key = copy_to_store_catalog(product_id, store_id, modifications)
                if store_catalog_key:
                    logger.info(f"Copied to store catalog: {store_catalog_key}")
                    # Trigger KB refresh for store
                    trigger_kb_refresh(store_id)
            except Exception as e:
                logger.warning(f"Failed to copy to store catalog: {str(e)}")
                # Continue processing even if store catalog fails
        
        elif event_type == 'product_update' and product_id and store_id:
            # Update product in store catalog
            try:
                modifications = {}
                if 'products' in raw_payload and 'product_variants' in raw_payload['products']:
                    variants = raw_payload['products']['product_variants']
                    if variants and isinstance(variants, list) and len(variants) > 0:
                        if 'price' in variants[0]:
                            modifications['price'] = variants[0]['price']
                
                store_catalog_key = copy_to_store_catalog(product_id, store_id, modifications)
                if store_catalog_key:
                    logger.info(f"Updated in store catalog: {store_catalog_key}")
                    # Trigger KB refresh for store
                    trigger_kb_refresh(store_id)
            except Exception as e:
                logger.warning(f"Failed to update store catalog: {str(e)}")
        
        elif event_type == 'product_delete' and product_id and store_id:
            # Delete product from store catalog
            try:
                delete_from_store_catalog(product_id, store_id)
                logger.info(f"Deleted from store catalog: {product_id} for store {store_id}")
                # Trigger KB refresh for store
                trigger_kb_refresh(store_id)
            except Exception as e:
                logger.warning(f"Failed to delete from store catalog: {str(e)}")
        
        # Determine routing target
        routing_target = get_routing_target(event_type)
        logger.info(f"Routing target: {routing_target}")
        
        # Register event in DynamoDB
        register_event(
            payload_hash=payload_hash,
            event_id=event_id,
            event_type=event_type,
            s3_key=raw_s3_key,  # Store raw S3 key for audit trail reference
            routing_target=routing_target,
            table=table,
            store_id=store_id
        )
        
        # TODO: Route to downstream systems (placeholder)
        # This would involve sending to SQS, EventBridge, or another Lambda
        
        response_body = {
            'status': 'success',
            'event_id': event_id,
            'event_type': event_type,
            'routing_target': routing_target,
            'raw_s3_key': raw_s3_key,
            'payload_hash': payload_hash
        }
        
        if store_id:
            response_body['store_id'] = store_id
        if product_id:
            response_body['product_id'] = product_id
        if metadata_s3_key:
            response_body['metadata_s3_key'] = metadata_s3_key
        if master_catalog_key:
            response_body['master_catalog_key'] = master_catalog_key
        if store_catalog_key:
            response_body['store_catalog_key'] = store_catalog_key
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        
        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            })
        }

