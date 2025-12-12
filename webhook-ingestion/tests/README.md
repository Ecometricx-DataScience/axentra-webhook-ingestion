# Testing and Validation

This directory contains tests and validation scripts for the Axentra Webhook Ingestion System.

## Quick Start - Postman Tests

The fastest way to test the webhook infrastructure is using the Postman collection:

### Import into Postman

1. Open Postman
2. Click **Import** 
3. Import both files:
   - `Axentra_Webhook_Tests.postman_collection.json` - The test collection
   - `Axentra_Webhook_Tests.postman_environment.json` - Environment variables

### Webhook Endpoint

```
https://6qr5nqhezqesjepdnezacyl7wq0zacpi.lambda-url.us-east-1.on.aws/
```

### Test Coverage

| Category | Tests |
|----------|-------|
| **Product Events** | New Product, Update, Delete, Full Payload |
| **Store Events** | New Store, Update, Delete, Auto-ID Generation |
| **Idempotency** | Duplicate Detection, Same Payload Handling |
| **Edge Cases** | Minimal Payload, Empty Payload, Unicode, Multiple Variants |
| **Health Check** | Lambda Response, Response Time |

### Running Tests

1. Select the "Axentra Webhook - Production" environment
2. Run individual requests or use Collection Runner for all tests
3. View test results in the Postman Test Results tab

### Expected Response (Success)

```json
{
  "status": "success",
  "event_id": "8d700f3d475f5d9d-1765502423",
  "event_type": "product_create",
  "routing_target": "product-service",
  "raw_s3_key": "store-id/product_create/2025/12/12/event-id.json",
  "payload_hash": "sha256-hash",
  "store_id": "your-store-id",
  "product_id": "your-product-id"
}
```

### Expected Response (Duplicate)

```json
{
  "status": "duplicate",
  "message": "Event already processed",
  "event_id": "original-event-id",
  "original_processing_timestamp": "2024-12-12T01:00:00Z"
}
```

---

## Additional Tests

### Local Tests (No AWS Required)

### 1. Lambda Function Logic Tests (`test_lambda_logic.py`)

Tests the core Lambda function logic without requiring AWS:

- ✅ **Field Stripping** - Verifies all specified fields are removed
- ✅ **Hash Calculation** - Tests SHA-256 payload hashing for idempotency
- ✅ **Event Type Detection** - Validates event type detection logic
- ✅ **Routing Logic** - Tests routing target determination
- ✅ **Metadata Enrichment** - Verifies metadata is added correctly
- ✅ **S3 Key Generation** - Validates date-based partitioning format
- ✅ **Full Payload Schema** - Tests with complete Axentra payload structure

**Run:**
```bash
cd webhook-ingestion
python3 tests/test_lambda_logic.py
```

### 2. Infrastructure Validation (`validate_infrastructure.sh`)

Validates infrastructure scripts and configuration files:

- ✅ **Bash Script Syntax** - Checks all `.sh` files for syntax errors
- ✅ **JSON Configuration** - Validates all JSON config files
- ✅ **Python Syntax** - Checks Lambda function Python syntax
- ✅ **Required Files** - Verifies all necessary files exist
- ✅ **Environment Variables** - Checks environment variable usage
- ✅ **S3 Bucket Name Consistency** - Validates bucket name across files

**Run:**
```bash
cd webhook-ingestion
./tests/validate_infrastructure.sh
```

### 3. Sample Payloads (`test_sample_payloads.json`)

Contains sample payloads for testing:
- `product_create` - Full product creation payload
- `product_delete` - Product deletion payload
- `minimal` - Minimal payload for edge case testing

## Running All Tests

```bash
cd webhook-ingestion

# Run Lambda logic tests
python3 tests/test_lambda_logic.py

# Run infrastructure validation
./tests/validate_infrastructure.sh
```

## What These Tests Validate

### ✅ Can Test (No AWS Required)

1. **Lambda Function Logic**
   - Field stripping correctness
   - Hash calculation consistency
   - Event type detection accuracy
   - Routing logic correctness
   - Metadata enrichment
   - S3 key format validation

2. **Code Quality**
   - Python syntax validation
   - Bash script syntax validation
   - JSON configuration validation
   - File structure validation

3. **Configuration Consistency**
   - S3 bucket name consistency
   - Environment variable usage
   - Configuration file structure

### ❌ Cannot Test (Requires AWS)

1. **AWS Resource Creation**
   - Actual S3 bucket creation
   - DynamoDB table creation
   - Lambda function deployment
   - IAM role creation

2. **Integration Tests**
   - End-to-end webhook processing
   - S3 storage operations
   - DynamoDB write operations
   - EventBridge event routing

3. **Performance Tests**
   - Lambda execution time
   - S3 upload performance
   - DynamoDB query performance

## Test Results

All tests should pass before requesting IAM permissions. This ensures:
- Code logic is correct
- Configuration is valid
- Field stripping works as expected
- Event detection is accurate

## Next Steps After Tests Pass

Once all tests pass:
1. Request IAM permissions (see `docs/REQUIRED-IAM-PERMISSIONS.md`)
2. Run infrastructure setup scripts
3. Deploy Lambda function
4. Test with actual AWS resources




