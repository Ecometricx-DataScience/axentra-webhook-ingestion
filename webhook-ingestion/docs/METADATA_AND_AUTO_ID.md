# Store/Product Creation and Metadata Storage

## Overview

The webhook ingestion system now supports:
1. **Automatic Store Creation:** Creates store metadata when events reference stores that don't exist in our system
2. **Automatic Product Creation:** Creates products in master catalog when events reference products that don't exist
3. **Metadata Storage:** Automatic metadata file creation for store creation events

These features enable multitenancy in AWS by automatically onboarding new stores and products when they appear in webhook events.

## Store Metadata Storage

### When It's Created

Metadata files are automatically created when a `store_create` event is received.

### File Location

Metadata files are stored in the **same S3 folder** as the main event file:
- **Main Event:** `{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.json`
- **Metadata:** `{store_id}/{event_type}/{year}/{month}/{day}/{event_id}.metadata.json`

### Metadata Structure

```json
{
  "metadataAttributes": {
    "store": "store-name.myshopify.com",
    "store_id": "uuid",
    "product_id": "uuid"  // Optional, only if product_id is present in payload
  }
}
```

### Example

**Input Payload:**
```json
{
  "event_type": "new_store",
  "store_id": "223e4567-e89b-12d3-a456-426614174000",
  "store_domain": "store-new-store-232122222222222222396.myshopify.com"
}
```

**Generated Metadata File:**
```json
{
  "metadataAttributes": {
    "store": "store-new-store-232122222222222222396.myshopify.com",
    "store_id": "223e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Use Cases

- **Multitenancy Tracking:** Associates store domains with store IDs
- **Audit Trail:** Provides additional context for store creation events
- **Data Recovery:** Enables reconstruction of store metadata from S3

## Automatic Store/Product Creation

### Store Creation

**Trigger:** When an event references a `store_id` that doesn't exist in our system

**Process:**
1. System checks if store exists by looking for store_create events in S3
2. If store doesn't exist, creates store metadata automatically
3. Stores metadata in same location as store_create events
4. Continues processing the original event normally

**Example:**
```json
// Input: Product event for a store that doesn't exist yet
{
  "event_type": "product_create",
  "products": {
    "product_id": "123...",
    "store_id": "888e8888-e88b-88d8-a888-888888888888",
    "store_domain": "new-store.myshopify.com"
  }
}

// System automatically:
// 1. Detects store doesn't exist
// 2. Creates store metadata: {store_id}/store_create/{date}/{event_id}.metadata.json
// 3. Processes product event normally
```

### Product Creation

**Trigger:** When a product event references a `product_id` that doesn't exist in our system

**Process:**
1. System checks if product exists in master catalog
2. If product doesn't exist, creates it in master catalog
3. Uses payload data to populate product information
4. Continues processing the original event normally

**Example:**
```json
// Input: Product update for a product that doesn't exist yet
{
  "event_type": "product_update",
  "products": {
    "product_id": "999e9999-e99b-99d9-a999-999999999999",
    "name": "New Product",
    "store_id": "223e4567-e89b-12d3-a456-426614174000"
  }
}

// System automatically:
// 1. Detects product doesn't exist in master catalog
// 2. Creates product: master/products/{product_id}.json
// 3. Processes update event normally
```

### Benefits

1. **Automatic Onboarding:** New stores/products are automatically added to the system
2. **No Manual Intervention:** System handles new entities without errors
3. **Data Consistency:** Ensures all referenced stores/products exist before processing
4. **Multitenancy Support:** Enables seamless addition of new tenants

## Implementation Details

### Functions Added

1. **`get_store_domain(payload)`**
   - Extracts store domain from various payload locations
   - Checks: `store_domain`, `store_id.domain`, `products.store_domain`

2. **`get_company_id(payload)`**
   - Currently returns `store_id` (multitenancy by store)
   - Can be extended for separate company_id support

3. **`check_store_exists(store_id)`**
   - Checks if store exists by looking for store_create events in S3
   - Returns True if store exists, False otherwise

4. **`check_product_exists(product_id)`**
   - Checks if product exists in master catalog
   - Returns True if product exists, False otherwise

5. **`create_store_if_not_exists(store_id, payload, event_id)`**
   - Creates store metadata if store doesn't exist
   - Returns S3 key of created metadata, or None if store already exists

6. **`create_product_if_not_exists(product_id, payload)`**
   - Creates product in master catalog if product doesn't exist
   - Returns S3 key of created product, or None if product already exists

7. **`store_store_metadata(payload, event_type, event_id, store_id, product_id)`**
   - Creates metadata file for store creation events
   - Stores in same S3 folder as main event

### Lambda Handler Updates

The `lambda_handler` now:
1. Detects event type
2. Extracts store_id and product_id from payload
3. Checks if store exists, creates it if not
4. Checks if product exists (for product events), creates it if not
5. Stores metadata file for store_create events
6. Continues with normal processing

### S3 Structure

```
axentra-webhook-raw-audit/
  {store_id}/
    store_create/
      2025/
        12/
          09/
            {event_id}.json              # Main event
            {event_id}.metadata.json     # Metadata file
```

## Testing

### Test Store Creation with Metadata

```bash
./webhook-ingestion/tests/test-store-create.sh
```

### Test Auto-Generate Store ID

```bash
aws lambda invoke \
  --function-name axentra-webhook-processor \
  --payload file://webhook-ingestion/tests/test-auto-generate-store-id.json \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json

cat /tmp/response.json | jq '.body | fromjson | .store_id'
```

### Test Auto-Generate Product ID

```bash
aws lambda invoke \
  --function-name axentra-webhook-processor \
  --payload file://webhook-ingestion/tests/test-auto-generate-product-id.json \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json

cat /tmp/response.json | jq '.body | fromjson | .product_id'
```

## AWS Configuration

No additional AWS configuration is required. The existing Lambda permissions already include:
- ✅ S3 PutObject/GetObject (for metadata files)
- ✅ DynamoDB PutItem/GetItem/Query (for event registry)

The metadata files are stored in the same bucket (`axentra-webhook-raw-audit`) as the main events, so no new permissions are needed.

## Multitenancy Support

### Current Implementation

- **Company ID = Store ID:** Currently, `company_id` equals `store_id` (multitenancy by store)
- **S3 Partitioning:** All events partitioned by `store_id` for tenant isolation
- **Metadata Tracking:** Store creation events store metadata for tenant tracking

### Future Enhancements

- Separate `company_id` field support
- Company-level metadata storage
- Cross-tenant analytics (with proper access controls)

## Response Format

The Lambda response now includes `metadata_s3_key` for store creation events:

```json
{
  "status": "success",
  "event_id": "abc123-1234567890",
  "event_type": "store_create",
  "store_id": "223e4567-e89b-12d3-a456-426614174000",
  "raw_s3_key": "{store_id}/store_create/2025/12/09/{event_id}.json",
  "metadata_s3_key": "{store_id}/store_create/2025/12/09/{event_id}.metadata.json",
  "payload_hash": "..."
}
```

