# Axentra Webhook Ingestion System

A HIPAA-compliant webhook ingestion pipeline for Axentra Health that receives payloads from Supabase, strips unnecessary fields, routes events by type, and stores raw payloads in S3 with date-based partitioning.

## Features

- **Immutable Audit Trail:** All raw webhook payloads preserved in S3 for compliance
- **Performance Optimized:** Strips unnecessary fields early in the pipeline
- **Idempotent Processing:** Handles duplicate webhook deliveries gracefully
- **Observable Operations:** Comprehensive logging and monitoring at each stage
- **Cost Optimized:** Date-based partitioning and lifecycle policies
- **HIPAA Compliant:** Encryption at rest and in transit, 7-year retention

## Architecture

```
Supabase → EventBridge → Lambda → S3 (Raw) + DynamoDB (Registry) → Downstream
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Quick Start

### Prerequisites

- AWS CLI installed and configured
- AWS Account with appropriate permissions
- Python 3.13 (for Lambda runtime)

### Setup

1. Navigate to infrastructure directory:
   ```bash
   cd webhook-ingestion/infrastructure
   ```

2. Run setup script:
   ```bash
   ./setup-infrastructure.sh
   ```

3. Configure EventBridge API destination with actual Supabase webhook URL and authentication

See [SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Project Structure

```
webhook-ingestion/
├── lambda/
│   └── webhook_processor.py    # Main Lambda function
├── infrastructure/
│   ├── setup-infrastructure.sh  # Main setup script
│   ├── setup-s3-bucket.sh       # S3 bucket setup
│   ├── setup-dynamodb.sh        # DynamoDB table setup
│   ├── setup-iam-role.sh         # IAM role setup
│   ├── setup-lambda.sh           # Lambda deployment
│   ├── setup-eventbridge.sh     # EventBridge setup
│   └── cleanup-infrastructure.sh # Cleanup script
├── config/
│   ├── lambda-trust-policy.json      # IAM trust policy
│   └── lambda-permissions-policy.json # IAM permissions policy
└── docs/
    ├── ARCHITECTURE.md    # System architecture
    ├── SETUP.md           # Setup instructions
    ├── HIPAA.md           # HIPAA compliance considerations
    └── FIELD_MAPPING.md   # Field stripping documentation
```

## Components

### Lambda Function (`webhook_processor`)

Processes webhook events with:
- Payload hash calculation for idempotency
- Field stripping (removes unnecessary fields)
- Event type detection
- Raw payload storage to S3
- Event registration in DynamoDB
- Metadata enrichment

### S3 Raw Audit Bucket

- **Name:** `axentra-webhook-raw-audit`
- **Partitioning:** `{event_type}/{year}/{month}/{day}/{event_id}.json`
- **Features:** Versioning, encryption, lifecycle policies

### DynamoDB Event Registry

- **Table:** `axentra-webhook-events`
- **Purpose:** Idempotency checking, event tracking, routing configuration
- **TTL:** 7 years (automatic cleanup)

### EventBridge

- **API Destination:** Receives webhooks from Supabase
- **Rule:** Routes events to Lambda function
- **Connection:** Handles authentication

## Field Stripping

The system strips the following fields to optimize performance:

- **Products:** `created_at`, `updated_at`, `archived_at`
- **Product Variants:** `image_url`, `stock_quantity`, `is_default`, `stockStatus`, `lab_test_codes_id`, `service_product_id`, `cpr_price`, `archived_at`
- **Categories:** `user_id`, `created_at`, `last_modified`, `image`

See [FIELD_MAPPING.md](docs/FIELD_MAPPING.md) for complete field mapping.

## HIPAA Compliance

The system implements:
- Encryption at rest (S3 SSE-S3, DynamoDB encryption)
- Encryption in transit (HTTPS/TLS)
- Immutable audit trail (S3 versioning)
- 7-year retention for compliance
- Access controls and logging

See [HIPAA.md](docs/HIPAA.md) for detailed compliance considerations.

## Testing

Test the Lambda function with a sample payload:

```bash
aws lambda invoke \
  --function-name axentra-webhook-processor \
  --payload file://test-payload.json \
  --region us-east-1 \
  response.json
```

## Cleanup

To remove all created resources:

```bash
cd webhook-ingestion/infrastructure
./cleanup-infrastructure.sh
```

**Warning:** This will delete all data including S3 objects and DynamoDB records.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [Setup Instructions](docs/SETUP.md) - Detailed setup and configuration
- [HIPAA Compliance](docs/HIPAA.md) - Compliance considerations and checklist
- [Field Mapping](docs/FIELD_MAPPING.md) - Field stripping documentation

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review CloudWatch logs for Lambda function
3. Verify IAM permissions and policies
4. Check EventBridge rule and API destination configuration

## License

Internal use only - Axentra Health project

