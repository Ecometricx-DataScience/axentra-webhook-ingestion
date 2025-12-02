# Axentra Webhook Ingestion System - Setup Instructions

## Prerequisites

1. **AWS CLI** installed and configured
2. **AWS Account** with appropriate permissions
3. **IAM Permissions** required:
   - `s3:CreateBucket`, `s3:PutBucketVersioning`, `s3:PutBucketEncryption`, `s3:PutBucketLifecycleConfiguration`
   - `dynamodb:CreateTable`, `dynamodb:DescribeTable`, `dynamodb:UpdateTimeToLive`
   - `iam:CreateRole`, `iam:PutRolePolicy`, `iam:AttachRolePolicy`, `iam:PassRole`
   - `lambda:CreateFunction`, `lambda:UpdateFunctionCode`, `lambda:AddPermission`
   - `events:PutRule`, `events:PutTargets`, `events:CreateConnection`, `events:CreateApiDestination`

## Quick Start

### 1. Navigate to Infrastructure Directory

```bash
cd webhook-ingestion/infrastructure
```

### 2. Run Setup Script

```bash
./setup-infrastructure.sh
```

This script will:
1. Create S3 bucket with versioning and lifecycle policies
2. Create DynamoDB table for event registry
3. Create IAM role for Lambda execution
4. Create and deploy Lambda function
5. Create EventBridge rule and API destination

### 3. Configure EventBridge API Destination

After setup, you need to configure the actual Supabase webhook endpoint:

```bash
# Update the API destination with actual endpoint
aws events update-api-destination \
  --name axentra-webhook-endpoint \
  --invocation-endpoint "https://your-supabase-webhook-url.com/webhook" \
  --region us-east-1
```

### 4. Configure Authentication

Update the EventBridge connection with actual Supabase authentication:

```bash
# Update connection with actual API key
aws events update-connection \
  --name axentra-webhook-connection \
  --auth-parameters '{
    "ApiKeyAuthParameters": {
      "ApiKeyName": "x-api-key",
      "ApiKeyValue": "YOUR_ACTUAL_API_KEY"
    }
  }' \
  --region us-east-1
```

## Manual Setup Steps

If you prefer to run setup scripts individually:

### Step 1: Create S3 Bucket

```bash
./setup-s3-bucket.sh
```

### Step 2: Create DynamoDB Table

```bash
./setup-dynamodb.sh
```

### Step 3: Create IAM Role

```bash
./setup-iam-role.sh
```

### Step 4: Deploy Lambda Function

```bash
./setup-lambda.sh
```

### Step 5: Setup EventBridge

```bash
./setup-eventbridge.sh
```

## Environment Variables

The Lambda function uses the following environment variables (set automatically by setup script):

- `S3_RAW_AUDIT_BUCKET`: S3 bucket name for raw payload storage
- `DYNAMODB_TABLE_NAME`: DynamoDB table name for event registry
- `EVENT_VERSION`: Event schema version (default: 1.0)

## Testing

### Test with Sample Payload

Create a test event:

```bash
aws lambda invoke \
  --function-name axentra-webhook-processor \
  --payload '{
    "detail": {
      "products": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Product",
        "description": "Test Description",
        "manufacturer": "Test Manufacturer",
        "needs_prescription": false,
        "product_variants": [
          {
            "id": "223e4567-e89b-12d3-a456-426614174000",
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Variant 1",
            "variant_name": "Standard",
            "price": 29.99,
            "sku": "TEST-SKU-001",
            "status": "NEW"
          }
        ]
      }
    }
  }' \
  --region us-east-1 \
  response.json

cat response.json
```

### Verify S3 Storage

```bash
# List objects in bucket
aws s3 ls s3://axentra-webhook-raw-audit/ --recursive
```

### Verify DynamoDB Registration

```bash
# Scan table (for testing only)
aws dynamodb scan \
  --table-name axentra-webhook-events \
  --region us-east-1
```

## Troubleshooting

### Permission Errors

If you encounter permission errors, check:

1. **IAM Permissions:** Ensure your AWS user/role has all required permissions
2. **Lambda Role:** Verify the Lambda execution role has correct policies attached
3. **S3 Bucket Policy:** Check bucket policies if S3 operations fail

### Lambda Function Errors

Check CloudWatch Logs:

```bash
aws logs tail /aws/lambda/axentra-webhook-processor --follow
```

### EventBridge Not Receiving Events

1. Verify API destination endpoint is correct
2. Check connection authentication
3. Verify EventBridge rule is enabled
4. Check Lambda function permissions for EventBridge

## Post-Setup Configuration

### 1. Configure Supabase Webhook

In your Supabase project:
1. Navigate to Database → Webhooks
2. Create new webhook
3. Set endpoint to EventBridge API destination URL
4. Configure authentication headers
5. Select events to trigger webhook

### 2. Set Up Monitoring

Create CloudWatch alarms for:
- Lambda error rate
- Lambda duration
- S3 PUT failures
- DynamoDB write failures

### 3. Configure Downstream Routing

Update the `get_routing_target()` function in `webhook_processor.py` to route events to actual downstream systems (SQS, EventBridge, etc.).

## Support

For issues or questions, refer to:
- Architecture documentation: `docs/ARCHITECTURE.md`
- HIPAA considerations: `docs/HIPAA.md`
- Field mapping: `docs/FIELD_MAPPING.md`

