# Field Mapping and Stripping Documentation

## Overview

This document details which fields are stripped from the webhook payload and why, as well as the complete field mapping for the Axentra webhook payload schema.

## Complete Payload Schema

### Products Object

```json
{
  "products": {
    "id": "string (UUID)",
    "name": "string",
    "description": "string",
    "dosage_instructions": "string | null",
    "manufacturer": "string",
    "needs_prescription": "boolean | null",
    "needs_telemed": "boolean | null",
    "store_id": "string (UUID) | null",
    "user_id": "string (UUID) | null",
    "category_ids": ["string (UUID)"],
    "status": "string | null",
    "created_at": "string (ISO 8601 timestamp) | null",      // STRIPPED
    "updated_at": "string (ISO 8601 timestamp) | null",      // STRIPPED
    "archived_at": "string (ISO 8601 timestamp) | null",      // STRIPPED
    "product_variants": [...],
    "categories": [...]
  }
}
```

### Product Variants Array

```json
{
  "product_variants": [
    {
      "id": "string (UUID)",
      "product_id": "string (UUID)",
      "name": "string",
      "variant_name": "string",
      "price": "number",
      "image_url": "string (URL)",                            // STRIPPED
      "sku": "string",
      "stock_quantity": "number (integer)",                  // STRIPPED
      "is_default": "boolean",                               // STRIPPED
      "stockStatus": "'In Stock' | 'Low Stock' | 'Out of Stock' | null",  // STRIPPED
      "status": "'NEW' | 'OLD' | null",
      "archived_at": "string (ISO 8601 timestamp) | null",   // STRIPPED
      "lab_test_codes_id": ["string (UUID)"],                // STRIPPED
      "service_product_id": "string | null",                 // STRIPPED
      "cpr_price": "number | null"                           // STRIPPED
    }
  ]
}
```

### Categories Array

```json
{
  "categories": [
    {
      "id": "string (UUID)",
      "name": "string",
      "is_featured": "boolean",
      "store_id": "string (UUID)",
      "user_id": "string (UUID)",                            // STRIPPED
      "created_at": "string (ISO 8601 timestamp) | null",   // STRIPPED
      "last_modified": "string (ISO 8601 timestamp) | null", // STRIPPED
      "image": "string (URL) | null"                          // STRIPPED
    }
  ]
}
```

## Fields Stripped

### From Products

| Field | Reason |
|-------|--------|
| `created_at` | Timestamp metadata not needed for processing |
| `updated_at` | Timestamp metadata not needed for processing |
| `archived_at` | Timestamp metadata not needed for processing |

### From Product Variants

| Field | Reason |
|-------|--------|
| `image_url` | Image URLs not needed for core processing |
| `stock_quantity` | Inventory data not needed |
| `is_default` | UI/display metadata not needed |
| `stockStatus` | Inventory status not needed |
| `lab_test_codes_id` | Lab test codes not needed for core processing |
| `service_product_id` | Service product reference not needed |
| `cpr_price` | CPR price may confuse LLM, store price is sufficient |
| `archived_at` | Timestamp metadata not needed for processing |

### From Categories

| Field | Reason |
|-------|--------|
| `user_id` | User identifier not needed for category processing |
| `created_at` | Timestamp metadata not needed for processing |
| `last_modified` | Timestamp metadata not needed for processing |
| `image` | Image URLs not needed for core processing |

## Fields Retained

### Products - Retained Fields

- `id` - Required for identification
- `name` - Core product information
- `description` - Core product information
- `dosage_instructions` - Important medical information
- `manufacturer` - Important product information
- `needs_prescription` - Important medical flag
- `needs_telemed` - Important medical flag
- `store_id` - Required for routing
- `user_id` - May be needed for processing (not stripped from products, only from categories)
- `category_ids` - Required for categorization
- `status` - Important status information
- `product_variants` - Core product data
- `categories` - Core category data

### Product Variants - Retained Fields

- `id` - Required for identification
- `product_id` - Required for relationship
- `name` - Core variant information
- `variant_name` - Core variant information
- `price` - Core pricing information
- `sku` - Required for inventory/product identification
- `status` - Important status information

### Categories - Retained Fields

- `id` - Required for identification
- `name` - Core category information
- `is_featured` - Important display flag
- `store_id` - Required for routing

## Processing Flow

1. **Raw Payload Received:** Complete payload with all fields
2. **Raw Storage:** Complete payload stored in S3 (immutable audit trail)
3. **Field Stripping:** Unnecessary fields removed
4. **Metadata Enrichment:** Processing metadata added
5. **Downstream Processing:** Stripped payload used for further processing

## Rationale for Field Stripping

### Performance Optimization
- Reduced payload size = faster processing
- Less data to transfer and store
- Lower storage costs

### LLM Processing
- Remove fields that may confuse language models
- Focus on essential product information
- Reduce noise in data

### Storage Efficiency
- Store only necessary data in processed format
- Raw payloads still available in S3 for audit
- Lifecycle policies optimize long-term storage

## Metadata Added

After field stripping, the following metadata is added:

```json
{
  "_metadata": {
    "processing_timestamp": "2024-01-15T10:30:00Z",
    "payload_hash": "sha256-hash-of-original-payload",
    "event_version": "1.0",
    "event_type": "product_create"
  }
}
```

## Event Type Detection

Event types are determined by analyzing the payload structure:

- **product_create:** New product (no archived_at, has new product data)
- **product_update:** Product modification (has id, updated data)
- **product_delete:** Product deletion (archived_at present)
- **store_create:** New store creation
- **store_update:** Store modification
- **store_delete:** Store deletion
- **unknown:** Unable to determine

## Future Considerations

If additional fields need to be stripped:

1. Update `FIELDS_TO_STRIP` dictionary in `webhook_processor.py`
2. Add field to appropriate section (products, product_variants, categories)
3. Update this documentation
4. Test with sample payloads
5. Deploy updated Lambda function

## Testing Field Stripping

To verify field stripping is working correctly:

```python
# Sample test payload
test_payload = {
    "products": {
        "id": "123",
        "name": "Test Product",
        "created_at": "2024-01-01T00:00:00Z",  # Should be stripped
        "product_variants": [{
            "id": "456",
            "image_url": "https://example.com/image.jpg",  # Should be stripped
            "stock_quantity": 100  # Should be stripped
        }]
    }
}

# After stripping, these fields should be removed
```


