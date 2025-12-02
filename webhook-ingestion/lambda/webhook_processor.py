import json
import boto3
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

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


def detect_event_type(payload: Dict[str, Any]) -> str:
    """
    Determine event type based on payload structure.
    
    Args:
        payload: The webhook payload
        
    Returns:
        Event type string (product_create, product_update, product_delete, etc.)
    """
    # Check for products in payload
    if 'products' in payload:
        products = payload['products']
        
        # Check if this is a deletion (archived_at present and not null)
        if isinstance(products, dict) and products.get('archived_at'):
            return 'product_delete'
        
        # Check if this is an update (has id and updated_at)
        if isinstance(products, dict) and products.get('id'):
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


def store_raw_payload(payload: Dict[str, Any], event_type: str, event_id: str) -> str:
    """
    Store raw payload to S3 with date-based partitioning.
    
    Args:
        payload: The raw webhook payload
        event_type: The detected event type
        event_id: Unique event identifier
        
    Returns:
        S3 key where the payload was stored
    """
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # S3 key: {event_type}/{year}/{month}/{day}/{event_id}.json
    s3_key = f"{event_type}/{year}/{month}/{day}/{event_id}.json"
    
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


def store_processed_payload(payload: Dict[str, Any], event_type: str, event_id: str) -> str:
    """
    Store processed/stripped payload to S3 with date-based partitioning.
    
    Args:
        payload: The processed/stripped webhook payload
        event_type: The detected event type
        event_id: Unique event identifier
        
    Returns:
        S3 key where the processed payload was stored
    """
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # S3 key: {event_type}/{year}/{month}/{day}/{event_id}.json
    s3_key = f"{event_type}/{year}/{month}/{day}/{event_id}.json"
    
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


def register_event(
    payload_hash: str,
    event_id: str,
    event_type: str,
    s3_key: str,
    routing_target: str,
    table
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
    """
    now = datetime.utcnow()
    processing_timestamp = now.isoformat() + 'Z'
    
    # TTL: 7 years from now (in seconds)
    ttl = int((now.timestamp() + (7 * 365 * 24 * 60 * 60)))
    
    try:
        table.put_item(
            Item={
                'payload_hash': payload_hash,
                'processing_timestamp': processing_timestamp,
                'event_id': event_id,
                'event_type': event_type,
                's3_key': s3_key,
                'status': 'processed',
                'routing_target': routing_target,
                'ttl': ttl
            }
        )
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
        logger.info(f"Detected event type: {event_type}")
        
        # Store raw payload to S3 (immutable audit trail)
        raw_s3_key = store_raw_payload(raw_payload, event_type, event_id)
        
        # Strip unnecessary fields
        stripped_payload = strip_fields(raw_payload)
        logger.info("Stripped unnecessary fields from payload")
        
        # Enrich with metadata
        enriched_payload = enrich_payload(stripped_payload, payload_hash, event_type)
        
        # Store processed payload to S3
        processed_s3_key = store_processed_payload(enriched_payload, event_type, event_id)
        
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
            table=table
        )
        
        # TODO: Route to downstream systems (placeholder)
        # This would involve sending to SQS, EventBridge, or another Lambda
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'event_id': event_id,
                'event_type': event_type,
                'routing_target': routing_target,
                'raw_s3_key': raw_s3_key,
                'processed_s3_key': processed_s3_key,
                'payload_hash': payload_hash
            })
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

