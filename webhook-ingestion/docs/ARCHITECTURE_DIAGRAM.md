# Axentra Webhook Ingestion System - Architecture Diagram

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUPABASE (Axentra Health)                         │
│                         Webhook Source System                               │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 │ HTTPS POST
                                 │ Webhook Payload (JSON)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AWS EVENTBRIDGE                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  API Destination: axentra-webhook-endpoint                           │  │
│  │  - Receives webhook from Supabase                                     │  │
│  │  - Validates authentication (API key)                                 │  │
│  │  - Rate limiting: 10 req/sec                                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Connection: axentra-webhook-connection                                │  │
│  │  - Authentication: API Key (Supabase credentials)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Rule: axentra-webhook-rule                                            │  │
│  │  - Event Pattern: source = "axentra.webhook"                          │  │
│  │  - Target: Lambda Function                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ EventBridge Event
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS LAMBDA FUNCTION                                      │
│              axentra-webhook-processor                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Runtime: Python 3.13                                                 │  │
│  │  Memory: 256 MB                                                        │  │
│  │  Timeout: 60 seconds                                                   │  │
│  │  Role: axentra-webhook-processor-role                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Processing Flow:                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. Receive EventBridge event                                         │  │
│  │  2. Extract payload from event.detail                                 │  │
│  │  3. Calculate SHA-256 hash of payload                                  │  │
│  │  4. Check DynamoDB for duplicate (idempotency)                        │  │
│  │     ├─ If duplicate → Return early with existing event info           │  │
│  │     └─ If new → Continue processing                                    │  │
│  │  5. Generate event_id: {hash[:16]}-{timestamp}                        │  │
│  │  6. Detect event_type (product_create/update/delete, etc.)             │  │
│  │  7. Store RAW payload to S3 (immutable audit trail)                    │  │
│  │  8. Strip unnecessary fields (13 fields removed)                      │  │
│  │  9. Enrich with metadata (timestamp, hash, version, event_type)        │  │
│  │  10. Store PROCESSED payload to S3                                     │  │
│  │  11. Register event in DynamoDB                                        │  │
│  │  12. Determine routing target                                          │  │
│  │  13. Return success response                                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│   S3 RAW AUDIT BUCKET │  │ S3 PROCESSED BUCKET    │  │   DYNAMODB TABLE      │
│ axentra-webhook-      │  │ axentra-webhook-       │  │ axentra-webhook-      │
│   raw-audit           │  │   processed            │  │   events              │
├───────────────────────┤  ├───────────────────────┤  ├───────────────────────┤
│ Purpose:              │  │ Purpose:               │  │ Purpose:               │
│ Immutable audit trail │  │ Processed data for      │  │ Idempotency tracking  │
│ HIPAA compliance      │  │ downstream systems     │  │ Event registry        │
│                       │  │                        │  │ Quick lookups         │
├───────────────────────┤  ├───────────────────────┤  ├───────────────────────┤
│ Configuration:        │  │ Configuration:         │  │ Schema:                │
│ - Versioning: Enabled │  │ - Versioning: Enabled  │  │ - PK: payload_hash    │
│ - Encryption: SSE-S3  │  │ - Encryption: SSE-S3   │  │ - SK: processing_     │
│ - Lifecycle:          │  │ - Lifecycle:           │  │   timestamp           │
│   • Glacier @ 90 days │  │   • Glacier @ 90 days  │  │ - TTL: 7 years         │
│   • Delete @ 7 years │  │   • Delete @ 7 years    │  │ - Billing: On-demand  │
│ - Public: Blocked     │  │ - Public: Blocked      │  │                       │
├───────────────────────┤  ├───────────────────────┤  ├───────────────────────┤
│ Partitioning:         │  │ Partitioning:          │  │ Attributes:            │
│ {event_type}/         │  │ {event_type}/          │  │ - event_id            │
│ {year}/               │  │ {year}/                │  │ - event_type          │
│ {month}/              │  │ {month}/               │  │ - s3_key (raw)        │
│ {day}/                │  │ {day}/                 │  │ - status             │
│ {event_id}.json       │  │ {event_id}.json         │  │ - routing_target      │
│                       │  │                        │  │ - ttl                 │
├───────────────────────┤  ├───────────────────────┤  ├───────────────────────┤
│ Example:              │  │ Example:               │  │ Example:               │
│ product_create/       │  │ product_create/        │  │ payload_hash: abc123  │
│ 2024/01/15/           │  │ 2024/01/15/            │  │ timestamp: 2024-01-15 │
│ abc123-1705276800.json│  │ abc123-1705276800.json │  │ event_id: abc123-...  │
│                       │  │                        │  │ event_type: product_  │
│                       │  │                        │  │   create              │
│                       │  │                        │  │ s3_key: product_...    │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

## Data Flow Diagram

```
┌──────────────┐
│   Supabase   │
│   Webhook    │
└──────┬───────┘
       │
       │ 1. HTTPS POST
       │    {products: {...}}
       ▼
┌──────────────────┐
│  EventBridge     │
│  API Destination │
└──────┬───────────┘
       │
       │ 2. Validate & Route
       ▼
┌──────────────────┐
│  Lambda Function │
│  ┌─────────────┐ │
│  │ Calculate   │ │
│  │ Hash        │ │
│  └──────┬──────┘ │
│         │        │
│  ┌──────▼──────┐ │
│  │ Check       │ │
│  │ DynamoDB    │ │
│  │ (duplicate?)│ │
│  └──────┬──────┘ │
│         │        │
│    ┌────▼────┐   │
│    │ New?    │   │
│    └──┬──┬───┘   │
│       │  │       │
│    No │  │ Yes   │
│       │  │       │
│       │  └───┐   │
│       │      │   │
│       │  ┌───▼──────────────┐
│       │  │ Store RAW to S3  │
│       │  └───┬──────────────┘
│       │      │
│       │  ┌───▼──────────────┐
│       │  │ Strip Fields     │
│       │  └───┬──────────────┘
│       │      │
│       │  ┌───▼──────────────┐
│       │  │ Enrich Metadata │
│       │  └───┬──────────────┘
│       │      │
│       │  ┌───▼──────────────┐
│       │  │ Store PROCESSED  │
│       │  │ to S3            │
│       │  └───┬──────────────┘
│       │      │
│       │  ┌───▼──────────────┐
│       │  │ Register in      │
│       │  │ DynamoDB          │
│       │  └───┬──────────────┘
│       │      │
│       └──────┘
│            │
│            │ 3. Return Response
│            ▼
│      ┌─────────────┐
│      │   Success   │
│      │   Response  │
│      └─────────────┘
│
└──────────────────────────────┐
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │  Raw S3      │  │ Processed S3 │  │  DynamoDB    │
        │  Bucket      │  │ Bucket       │  │  Registry    │
        └──────────────┘  └──────────────┘  └──────────────┘
```

## Component Details

### 1. EventBridge API Destination
- **Name:** `axentra-webhook-endpoint`
- **Endpoint:** Supabase webhook URL (to be configured)
- **Method:** POST
- **Rate Limit:** 10 requests/second
- **Authentication:** API Key via Connection

### 2. Lambda Function
- **Name:** `axentra-webhook-processor`
- **Runtime:** Python 3.13
- **Memory:** 256 MB
- **Timeout:** 60 seconds
- **Environment Variables:**
  - `S3_RAW_AUDIT_BUCKET`: `axentra-webhook-raw-audit`
  - `S3_PROCESSED_BUCKET`: `axentra-webhook-processed`
  - `DYNAMODB_TABLE_NAME`: `axentra-webhook-events`
  - `EVENT_VERSION`: `1.0`

### 3. S3 Raw Audit Bucket
- **Name:** `axentra-webhook-raw-audit`
- **Purpose:** Immutable audit trail for HIPAA compliance
- **Storage:** Complete original payloads
- **Retention:** 7 years (lifecycle policy)
- **Partitioning:** `{event_type}/{year}/{month}/{day}/{event_id}.json`

### 4. S3 Processed Bucket
- **Name:** `axentra-webhook-processed`
- **Purpose:** Processed/stripped payloads for downstream systems
- **Storage:** Field-stripped + metadata-enriched payloads
- **Retention:** 7 years (lifecycle policy)
- **Partitioning:** `{event_type}/{year}/{month}/{day}/{event_id}.json`

### 5. DynamoDB Event Registry
- **Table:** `axentra-webhook-events`
- **Partition Key:** `payload_hash` (String)
- **Sort Key:** `processing_timestamp` (String)
- **TTL:** `ttl` attribute (7 years)
- **Purpose:** Idempotency checking and event tracking

### 6. IAM Role
- **Name:** `axentra-webhook-processor-role`
- **Permissions:**
  - S3: PutObject, GetObject on both buckets
  - DynamoDB: PutItem, GetItem, Query on event registry
  - CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

## Field Stripping

**Fields Removed (13 total):**
- **Products:** `created_at`, `updated_at`, `archived_at`
- **Product Variants:** `image_url`, `stock_quantity`, `is_default`, `stockStatus`, `lab_test_codes_id`, `service_product_id`, `cpr_price`, `archived_at`
- **Categories:** `user_id`, `created_at`, `last_modified`, `image`

**Fields Kept:**
- All essential product data (id, name, description, price, etc.)
- All essential variant data (id, product_id, name, variant_name, price, sku, status)
- All essential category data (id, name, is_featured, store_id)

## Event Type Detection

Currently inferred from payload structure:
- `product_delete`: `archived_at` present and not null
- `product_update`: Has `id` (heuristic)
- `product_create`: Otherwise
- `unknown`: Cannot determine

**Note:** Ideally, Supabase should include explicit `event_type` field in payload.

## Routing Logic

**Current Mapping:**
- `product_create` → `product-service`
- `product_update` → `product-service`
- `product_delete` → `product-service`
- `store_create` → `store-service`
- `store_update` → `store-service`
- `store_delete` → `store-service`
- `unknown` → `default-handler`

**Future:** Downstream routing to SQS, EventBridge, or other Lambda functions.

## Security & Compliance

### Encryption
- **At Rest:** SSE-S3 (AES-256) on all S3 buckets
- **In Transit:** HTTPS/TLS for all communications
- **DynamoDB:** Encryption at rest (default)

### Access Control
- **IAM Roles:** Least privilege principle
- **S3 Buckets:** Public access blocked
- **DynamoDB:** IAM role-based access only

### Audit Trail
- **Raw Payloads:** Immutable storage with versioning
- **Event Registry:** Complete processing history
- **CloudWatch Logs:** All Lambda invocations logged
- **Retention:** 7 years for HIPAA compliance

## Monitoring & Observability

### CloudWatch Metrics
- Lambda invocations
- Lambda errors
- Lambda duration
- S3 PUT operations
- DynamoDB write operations

### CloudWatch Logs
- All Lambda function logs
- Error tracking
- Performance monitoring

## Cost Optimization

- **S3 Lifecycle:** Glacier after 90 days
- **DynamoDB:** On-demand billing (pay per request)
- **Field Stripping:** Reduced storage costs
- **Date Partitioning:** Efficient querying
- **TTL:** Automatic cleanup after retention period

## Scalability

- **Lambda:** Auto-scales based on EventBridge events
- **DynamoDB:** On-demand capacity (unlimited)
- **S3:** Unlimited storage
- **EventBridge:** High throughput (10 req/sec per destination)

