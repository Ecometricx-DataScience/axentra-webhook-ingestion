# Testing and Validation

This directory contains tests and validation scripts that can be run **without AWS IAM permissions**. These tests validate the Lambda function logic, infrastructure scripts, and configuration files.

## Available Tests

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




