# Store Catalog Architecture

## Overview

The Axentra webhook ingestion system implements a master/store catalog architecture to manage product information across multiple stores. This design separates the master product definition from store-specific customizations (e.g., pricing).

## Architecture

```
┌─────────────────────┐
│  Master Catalog     │
│  (Complete Product) │
│  master/products/   │
└──────────┬──────────┘
           │
           │ Copy with modifications
           │
           ▼
┌─────────────────────┐
│  Store Catalogs     │
│  (Store-Specific)    │
│  stores/{id}/       │
└─────────────────────┘
```

## S3 Structure

### Master Catalog
**Path:** `master/products/{product_id}.json`

**Purpose:** Single source of truth for complete product definitions. Contains all product information from Ben's form and webhook updates.

**Example:**
```json
{
  "products": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Product Name",
    "description": "Full description",
    "product_variants": [
      {
        "id": "variant-uuid",
        "price": 29.99,
        "name": "Variant Name"
      }
    ]
  }
}
```

### Store Catalogs
**Path:** `stores/{store_id}/products/{product_id}.json`

**Purpose:** Store-specific product instances with customizations (e.g., different pricing).

**Example:**
```json
{
  "products": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Product Name",
    "description": "Full description",
    "store_id": "223e4567-e89b-12d3-a456-426614174000",
    "product_variants": [
      {
        "id": "variant-uuid",
        "price": 24.99,  // Store-specific price
        "name": "Variant Name"
      }
    ]
  }
}
```

## Product Lifecycle

### 1. Product Creation
When a new product is created via webhook:

1. **Store to Master Catalog:**
   - Full product definition stored at `master/products/{product_id}.json`
   - This becomes the source of truth

2. **Copy to Store Catalog:**
   - Product copied from master to `stores/{store_id}/products/{product_id}.json`
   - Store-specific modifications applied (e.g., price from webhook)
   - `store_id` added to product object

3. **Trigger KB Refresh:**
   - SNS message published to `axentra-kb-refresh` topic
   - Downstream systems refresh Knowledge Base for the store

### 2. Product Update
When a product is updated via webhook:

1. **Update Master Catalog:**
   - Product definition updated in `master/products/{product_id}.json`
   - Maintains single source of truth

2. **Update Store Catalog:**
   - Product copied from master with modifications
   - Store-specific changes applied (e.g., new price)
   - Existing store catalog entry replaced

3. **Trigger KB Refresh:**
   - SNS message published to refresh Knowledge Base

### 3. Product Deletion
When a product is deleted via webhook:

1. **Remove from Store Catalog:**
   - Product deleted from `stores/{store_id}/products/{product_id}.json`
   - Master catalog entry remains (for audit/history)

2. **Trigger KB Refresh:**
   - SNS message published to refresh Knowledge Base

## Catalog Management Functions

### `store_to_master_catalog(payload, product_id)`
Stores or updates product in master catalog.

**Input:**
- `payload`: Product payload (full or processed)
- `product_id`: Product identifier

**Output:**
- S3 key where product was stored

### `copy_to_store_catalog(product_id, store_id, modifications)`
Copies product from master to store catalog with modifications.

**Input:**
- `product_id`: Product identifier
- `store_id`: Store identifier
- `modifications`: Dictionary of modifications (e.g., `{"price": 24.99}`)

**Output:**
- S3 key where store product was stored

**Process:**
1. Fetch product from master catalog
2. Apply modifications (e.g., update variant prices)
3. Add `store_id` to product object
4. Store to store catalog

### `delete_from_store_catalog(product_id, store_id)`
Removes product from store-specific catalog.

**Input:**
- `product_id`: Product identifier
- `store_id`: Store identifier

**Process:**
1. Delete object from `stores/{store_id}/products/{product_id}.json`

## KB Refresh Trigger

### Purpose
When store catalogs change, downstream systems (e.g., Knowledge Base) need to be notified to refresh their data.

### Implementation
- **SNS Topic:** `axentra-kb-refresh`
- **Message Format:**
  ```json
  {
    "store_id": "uuid",
    "timestamp": "2024-01-15T12:00:00Z",
    "trigger": "webhook_processor"
  }
  ```

### Trigger Events
- Product added to store catalog
- Product updated in store catalog
- Product removed from store catalog

### Subscribers
Downstream systems can subscribe to the SNS topic to receive refresh notifications:
- Knowledge Base service
- Search index service
- API gateway cache invalidation

## Benefits

1. **Single Source of Truth:** Master catalog maintains complete product definitions
2. **Store Customization:** Each store can have different pricing/modifications
3. **Efficient Updates:** Changes propagate from master to stores
4. **Audit Trail:** Master catalog preserves history
5. **Scalability:** Store catalogs can be queried independently

## Data Consistency

- Master catalog is always updated first
- Store catalogs are derived from master
- If master product doesn't exist, webhook payload is used directly
- Store-specific modifications override master values

## Future Enhancements

1. **Bulk Operations:** Copy multiple products to store at once
2. **Store Templates:** Pre-configured product sets for new stores
3. **Price Rules:** Automatic price modifications based on store rules
4. **Catalog Sync:** Periodic sync to ensure consistency
5. **Versioning:** Track changes to master and store catalogs


