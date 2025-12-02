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
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│   S3     │  │ DynamoDB │  │ Downstream│
│  Raw     │  │ Registry │  │ Routing  │
│  Audit   │  │          │  │ (Future) │
└──────────┘  └──────────┘  └──────────┘
```

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
- **Field Stripping:** Removes unnecessary fields before processing
- **Event Type Detection:** Analyzes payload to determine event type
- **Raw Payload Storage:** Stores complete payload in S3 for audit trail
- **Event Registration:** Records event in DynamoDB for tracking
- **Metadata Enrichment:** Adds processing timestamp, hash, version, event type

**Processing Flow:**
1. Receive event from EventBridge
2. Calculate payload hash
3. Check DynamoDB for duplicate
4. Store raw payload to S3
5. Strip unnecessary fields
6. Detect event type
7. Enrich with metadata
8. Register in DynamoDB
9. Route to downstream (placeholder)

### 3. S3 Raw Audit Bucket

**Bucket Name:** `axentra-webhook-raw-audit`

**Partitioning Structure:**
```
{event_type}/{year}/{month}/{day}/{event_id}.json
```

**Example:**
```
product_create/2024/01/15/abc123def456-1705276800.json
```

**Configuration:**
- Versioning: Enabled (immutable audit trail)
- Encryption: SSE-S3 (AES256)
- Lifecycle:
  - Transition to Glacier after 90 days
  - Delete after 7 years
- Public Access: Blocked

### 4. DynamoDB Event Registry

**Table Name:** `axentra-webhook-events`

**Schema:**
- **Partition Key:** `payload_hash` (String) - SHA-256 hash of payload
- **Sort Key:** `processing_timestamp` (String) - ISO 8601 timestamp
- **Attributes:**
  - `event_id` (String) - Unique event identifier
  - `event_type` (String) - Detected event type
  - `s3_key` (String) - S3 location of raw payload
  - `status` (String) - Processing status
  - `routing_target` (String) - Downstream routing target
  - `ttl` (Number) - Time-to-live for automatic cleanup (7 years)

**Use Cases:**
- Idempotency checking
- Event tracking and audit
- Quick lookup for operational queries
- Routing configuration management

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

### 5. Routing
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

The system analyzes payload structure to determine event type:

- **product_create:** New product creation
- **product_update:** Product modification
- **product_delete:** Product deletion (archived_at present)
- **store_create:** New store creation
- **store_update:** Store modification
- **store_delete:** Store deletion
- **unknown:** Unable to determine type

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

