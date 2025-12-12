# Axentra Webhook Ingestion System - Architecture

## Overview

The Axentra Webhook Ingestion System is a HIPAA-compliant pipeline designed to receive, process, and store webhook events from Supabase. The system ensures data immutability, idempotency, and efficient processing through selective field stripping.

## System Architecture

```
┌─────────────┐
│  Supabase   │
│  Webhooks   │
└──────┬──────┘
       │ HTTPS
       │
       ▼
┌─────────────────┐
│  EventBridge    │
│  API Destination│
│  + Rule         │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Lambda         │
│  Processor      │
└──────┬──────────┘
       │
       ├──────────────┬──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│   S3     │  │ DynamoDB │  │   S3     │  │ DynamoDB │  │   SNS     │
│  Raw     │  │ Registry │  │ Processed│  │ Ben's    │  │ KB Refresh│
│  Audit   │  │ (Ours)   │  │ Catalogs │  │ Tables   │  │  Trigger  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │  Stores      │
                              │  Products    │
                              │ (Source of   │
                              │   Truth)     │
                              └──────────────┘

**Integration with Ben's Infrastructure:**
- Lambda checks/writes to Ben's DynamoDB tables (`axentra-stores`, `Product-kbtwy4tflncitfudusepuzm4nq-NONE`) as source of truth
- Our S3 buckets remain separate for audit trails and master catalogs
- See [BEN_INTEGRATION.md](./BEN_INTEGRATION.md) for details

## Component Details

### 1. EventBridge API Destination

**Purpose:** Receives webhook events from Supabase via HTTPS

**Configuration:**
- Endpoint: Supabase webhook URL (to be configured)
- Authentication: API key or OAuth (to be configured)
- Rate limiting: 10 requests per second

**Responsibilities:**
- Initial request validation
- Authentication/authorization
- Event routing to Lambda processor
- Dead letter queue for failed deliveries

### 2. Lambda Function (webhook_processor)

**Purpose:** Process webhook events, strip fields, and store data

**Key Functions:**
- **Idempotency Check:** Uses SHA-256 hash of payload to detect duplicates
- **Event Type Detection:** Uses explicit `event_type` field or infers from payload structure
- **Store/Product ID Extraction:** Extracts `store_id` and `product_id` from various payload structures
- **Ben's DynamoDB Integration:** Checks Ben's tables (`axentra-stores`, `Product-kbtwy4tflncitfudusepuzm4nq-NONE`) as source of truth for validation
- **Store/Product Existence Validation:** Validates that stores/products exist (checks Ben's DynamoDB tables first, then falls back to our S3 storage)
- **Note:** Store and product creation is handled by backend portals, NOT by webhooks. Webhooks only validate existence and process events.
- **Raw Payload Storage:** Stores complete payload in S3 with store_id partitioning (immutable audit trail)
- **Store Metadata Storage:** Stores metadata file for store creation events (enables multitenancy tracking)
- **Master Catalog Management:** Stores products to master catalog (`master/products/{product_id}.json`) - separate from webhook events
- **Store Catalog Management:** Copies products from master to store catalogs with modifications
- **KB Refresh Triggers:** Publishes to SNS topic to trigger Knowledge Base refresh
- **Event Registration:** Records event in DynamoDB for tracking (includes store_id)

**Processing Flow:**
1. Receive event from EventBridge
2. Detect event type (explicit field or inference)
3. Extract store_id and product_id from payload
4. **Validate store exists** (check Ben's DynamoDB - source of truth)
   - If store doesn't exist: Log warning (store should be created via backend portal)
5. **Validate product exists** (check Ben's DynamoDB - source of truth, for product events only)
   - If product doesn't exist: Log warning (product should be created via backend portal)
6. Calculate payload hash
7. Check our DynamoDB event registry for duplicate
8. If duplicate: return early with existing event info
9. If new: continue processing
10. Store raw payload to S3 (with store_id partitioning) - **immutable audit trail**
11. Store metadata file for store creation events (same folder, `.metadata.json` suffix)
12. Handle master/store catalog management based on event type:
    - Product create/update: Store to master catalog (separate from events), copy to store catalog
    - Product delete: Delete from store catalog
13. Trigger KB refresh (if store catalog changed)
14. Register in our DynamoDB event registry (with store_id)
15. Route to downstream (placeholder)

**Important:** Store and product creation is handled by backend portals, NOT by webhooks. The webhook system only validates that stores/products exist and processes events for existing entities.

**Note:** Master catalog is intentionally separate from webhook events. See [S3_BUCKET_SYSTEM.md](./S3_BUCKET_SYSTEM.md) for details.

### 3. S3 Buckets

**See [S3_BUCKET_SYSTEM.md](./S3_BUCKET_SYSTEM.md) for complete bucket system breakdown.**

#### Our S3 Buckets

##### Raw Audit Bucket
**Bucket Name:** `axentra-webhook-raw-audit`

**Purpose:** Immutable audit trail for all webhook events

**Partitioning Structure:**
```
{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json
{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.metadata.json  (for store_create events)
```

**Example:**
```
223e4567-e89b-12d3-a456-426614174000/product_create/2025/12/09/e8b78063c351200b-1765297638.json
223e4567-e89b-12d3-a456-426614174000/store_create/2025/12/09/459b42f742a0be95-1765312372.metadata.json
```

**Configuration:**
- Versioning: Enabled (immutable audit trail)
- Encryption: SSE-S3 (AES256)
- Lifecycle:
  - Transition to Glacier after 90 days
  - Delete after 7 years (HIPAA requirement)
- Public Access: Blocked

##### Processed Bucket
**Bucket Name:** `axentra-webhook-processed`

**Purpose:** Master product catalog and store-specific catalogs (intentionally separate from webhook events)

**Structures:**
1. **Master Product Catalog:** `master/products/{product_id}.json`
2. **Store-Specific Catalogs:** `stores/{store_id}/products/{product_id}.json`

**Example:**
```
# Master catalog (separate from webhook events)
master/products/123e4567-e89b-12d3-a456-426614174000.json

# Store catalog (for KB refresh)
stores/223e4567-e89b-12d3-a456-426614174000/products/123e4567-e89b-12d3-a456-426614174000.json
```

**Configuration:**
- Versioning: Enabled
- Encryption: SSE-S3 (AES256)
- Public Access: Blocked

**Why Separate from Webhook Events?**
- **Catalog Management:** Products are living entities that evolve over time
- **Webhook Events:** Events are immutable historical records
- **Different Lifecycles:** Catalogs are current state, events are audit trail
- **KB Refresh:** Store catalogs trigger Knowledge Base updates independently

#### Ben's S3 Bucket (Independent)

##### Product JSON Bucket
**Bucket Name:** `axentra-prod-productjson-302146782327`

**Purpose:** Product JSON files synced from Ben's DynamoDB Product table

**Structure:**
```
{productId}.json
```

**Example:**
```
12345.json
```

**Note:** This bucket is managed by Ben's `Axentra-Prod-StreamHandler` Lambda, which syncs DynamoDB → S3. Our system does NOT write to this bucket.

### 4. DynamoDB Tables

#### Our Event Registry Table
**Table Name:** `axentra-webhook-events`

**Schema:**
- **Partition Key:** `payload_hash` (String) - SHA-256 hash of payload
- **Sort Key:** `processing_timestamp` (String) - ISO 8601 timestamp
- **Attributes:**
  - `event_id` (String) - Unique event identifier
  - `event_type` (String) - Detected event type
  - `store_id` (String, optional) - Store identifier
  - `s3_key` (String) - S3 location of raw payload
  - `status` (String) - Processing status
  - `routing_target` (String) - Downstream routing target
  - `ttl` (Number) - Time-to-live for automatic cleanup (7 years)

**Use Cases:**
- Idempotency checking
- Event tracking and audit
- Quick lookup for operational queries
- Routing configuration management

#### Ben's DynamoDB Tables (Source of Truth)

**Integration:** Our Lambda checks/writes to Ben's tables for stores and products.

##### Stores Table
**Table Name:** `axentra-stores`

**Schema:**
- **Partition Key:** `store_id` (String)
- **Attributes:**
  - `store_domain` (String, optional)
  - `created_at` (String)

**Purpose:** Source of truth for store registry. Our Lambda checks this table first when processing store-related events.

##### Product Table
**Table Name:** `Product-kbtwy4tflncitfudusepuzm4nq-NONE`

**Schema:**
- **Partition Key:** `productId` (String)
- **Attributes:** GraphQL-style product fields (name, form, dose, uses, mechanism, etc.)

**Purpose:** Source of truth for product registry. Our Lambda checks this table first when processing product-related events.

**Note:** Ben's `Axentra-Prod-StreamHandler` Lambda syncs this table to S3 bucket `axentra-prod-productjson-302146782327`.

## Data Flow

### 1. Webhook Reception
- Supabase sends webhook to EventBridge API destination
- EventBridge validates and routes to Lambda

### 2. Processing
- Lambda calculates payload hash
- Checks DynamoDB for duplicate
- If duplicate: return early with existing event info
- If new: continue processing

### 3. Storage
- Store raw payload to S3 (immutable audit trail)
- Register event in DynamoDB

### 4. Transformation
- Strip unnecessary fields
- Enrich with metadata
- Detect event type

### 5. Catalog Management
- **Ben's DynamoDB:** Check/write to Ben's Product table (source of truth)
- **Our Master Catalog:** Store complete product definitions to `master/products/{product_id}.json` (separate from webhook events)
- **Store Catalogs:** Copy products from master to `stores/{store_id}/products/{product_id}.json` with store-specific modifications (e.g., price)
- **Product Lifecycle:**
  - Create/Update: Write to Ben's DynamoDB, store to our master catalog, copy to store catalog
  - Delete: Remove from store catalog (master and DynamoDB remain)

### 6. KB Refresh Trigger
- When store catalog changes, publish to SNS topic `axentra-kb-refresh`
- Downstream systems can subscribe to trigger Knowledge Base refresh
- Ensures store-specific product information is up-to-date

### 7. Routing
- Determine routing target based on event type
- Store routing decision in DynamoDB
- Placeholder for downstream integration

## Field Stripping

The system removes the following fields to optimize performance and reduce storage:

### Products
- `created_at`
- `updated_at`
- `archived_at`

### Product Variants
- `image_url`
- `stock_quantity`
- `is_default`
- `stockStatus`
- `lab_test_codes_id`
- `service_product_id`
- `cpr_price`
- `archived_at`

### Categories
- `user_id`
- `created_at`
- `last_modified`
- `image`

## Event Type Detection

The system supports two methods for event type detection:

### 1. Explicit Event Type (Preferred)
New simplified payloads include an explicit `event_type` field:
- `product_update` → `product_update`
- `product_deletion` → `product_delete`
- `new_product` → `product_create`
- `new_store` → `store_create`
- `deleted_store` → `store_delete`
- `updated_store` → `store_update`

### 2. Inference (Fallback)
For backward compatibility with original payloads, the system analyzes payload structure:
- **product_create:** New product creation
- **product_update:** Product modification (has id/product_id)
- **product_delete:** Product deletion (archived_at present)
- **store_create:** New store creation (triggers metadata file storage)
- **store_update:** Store modification
- **store_delete:** Store deletion
- **unknown:** Unable to determine type

## Auto-ID Generation

The system automatically generates `store_id` and `product_id` if they are missing from the payload. This enables multitenancy by ensuring every event has a unique store identifier.

### Store ID Generation
- **Trigger:** If `store_id` is missing from payload
- **Method:** Generates UUID v4
- **Storage:** Updates payload with generated ID before processing
- **Use Case:** Enables multitenancy when new stores are created without explicit IDs

### Product ID Generation
- **Trigger:** If `product_id` is missing from payload (for product events only)
- **Method:** Generates UUID v4
- **Storage:** Updates payload with generated ID before processing
- **Use Case:** Handles product creation events that don't include product IDs

### Multitenancy Support
- **Company ID:** Currently, `company_id` equals `store_id` (multitenancy by store)
- **Metadata Storage:** Store creation events store metadata files for tracking
- **S3 Partitioning:** All events are partitioned by `store_id` for tenant isolation

## Payload Formats

### New Simplified Payloads

**Product Update:**
```json
{
  "event_type": "product_update",
  "products": {
    "name": "Product Name",
    "product_id": "uuid",
    "store_id": "uuid",
    "product_variants": [{"price": 29.99}]
  }
}
```

**Product Deletion:**
```json
{
  "event_type": "product_deletion",
  "products": {
    "product_id": "uuid",
    "store_id": "uuid"
  }
}
```

**New Product:**
```json
{
  "event_type": "new_product",
  "products": {
    "name": "Product Name",
    "product_id": "uuid",
    "store_id": "uuid",
    "product_variants": [{"price": 19.99}]
  }
}
```

**Store Events:**
```json
{
  "event_type": "new_store|deleted_store|updated_store",
  "store_id": "uuid",  // Auto-generated if missing
  "store_domain": "store-name.myshopify.com"  // Optional, used for metadata
}
```

**Store Creation Metadata:**
When a `store_create` event is received, a metadata file is automatically stored alongside the main event file:
- **Main Event:** `{store_id}/store_create/{year}/{month}/{day}/{event_id}.json`
- **Metadata:** `{store_id}/store_create/{year}/{month}/{day}/{event_id}.metadata.json`

**Metadata Structure:**
```json
{
  "metadataAttributes": {
    "store": "store-name.myshopify.com",
    "store_id": "uuid",
    "product_id": "uuid"  // If product_id is present in payload
  }
}
```

This metadata enables multitenancy tracking in AWS by associating store domains with store IDs.

### Original Full Payloads
The system also supports the original full payload structure with all product fields. Field stripping will remove unnecessary fields as specified.

## Security Considerations

### HIPAA Compliance
- All data encrypted at rest (S3 SSE-S3)
- All data encrypted in transit (HTTPS)
- Immutable audit trail (S3 versioning)
- Access logging enabled
- No PII in processed payloads (fields stripped)
- 7-year retention for compliance

### Access Control
- IAM roles with least privilege
- S3 bucket policies restrict access
- DynamoDB access via IAM roles only
- Lambda execution role with minimal permissions
- SNS topic access for KB refresh triggers

## Monitoring and Observability

### CloudWatch Logs
- All Lambda invocations logged
- Error tracking and alerting
- Performance metrics

### Metrics to Monitor
- Lambda invocation count
- Lambda error rate
- Lambda duration
- S3 PUT operations
- DynamoDB write operations
- Duplicate event detection rate

## Cost Optimization

- Date-based partitioning for efficient S3 queries
- Lifecycle policies (Glacier after 90 days)
- DynamoDB on-demand billing
- TTL on DynamoDB items (automatic cleanup)
- Selective field processing (reduced storage)

## Scalability

- Lambda auto-scaling
- DynamoDB on-demand capacity
- S3 unlimited storage
- EventBridge high throughput
- Rate limiting on API destination