# Axentra Webhook Ingestion - Terraform Infrastructure

This directory contains Terraform Infrastructure as Code (IaC) for deploying the Axentra Webhook Ingestion System to AWS.

## Architecture

The Terraform configuration creates the following AWS resources:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   EventBridge   │────▶│     Lambda      │────▶│       S3        │
│  (API Dest +    │     │   (Processor)   │     │  (Raw Audit)    │
│   Connection)   │     └────────┬────────┘     └─────────────────┘
└─────────────────┘              │
                                 ▼
                        ┌─────────────────┐
                        │    DynamoDB     │
                        │ (Event Registry)│
                        └─────────────────┘
```

## Prerequisites

- Terraform >= 1.0.0
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create the required resources

## Files

| File | Description |
|------|-------------|
| `versions.tf` | Terraform and provider version constraints |
| `variables.tf` | Input variable definitions |
| `s3.tf` | S3 bucket for raw audit storage |
| `dynamodb.tf` | DynamoDB table for event registry |
| `iam.tf` | IAM roles and policies for Lambda |
| `lambda.tf` | Lambda function configuration |
| `eventbridge.tf` | EventBridge rule, connection, and API destination |
| `outputs.tf` | Output values after deployment |
| `terraform.tfvars.example` | Example variable values |

## Quick Start

1. **Initialize Terraform:**
   ```bash
   cd webhook-ingestion/terraform
   terraform init
   ```

2. **Create your variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. **Update `terraform.tfvars` with your values:**
   - Set `webhook_api_key` to your actual Supabase API key
   - Set `webhook_endpoint_url` to your actual Supabase webhook URL

4. **Review the plan:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

## Configuration Variables

### Required (Update before deployment)

| Variable | Description |
|----------|-------------|
| `webhook_api_key` | API key for Supabase webhook authentication |
| `webhook_endpoint_url` | Supabase webhook endpoint URL |

### Optional (With defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for deployment |
| `environment` | `Production` | Environment tag |
| `s3_bucket_name` | `axentra-webhook-raw-audit` | S3 bucket name |
| `dynamodb_table_name` | `axentra-webhook-events` | DynamoDB table name |
| `lambda_function_name` | `axentra-webhook-processor` | Lambda function name |
| `lambda_runtime` | `python3.13` | Lambda runtime |
| `lambda_timeout` | `60` | Lambda timeout (seconds) |
| `lambda_memory_size` | `256` | Lambda memory (MB) |

## HIPAA Compliance Features

The infrastructure is configured with HIPAA compliance in mind:

- **S3 Bucket:**
  - Versioning enabled for immutable audit trail
  - Server-side encryption (AES-256)
  - Public access blocked
  - Lifecycle policy: Glacier transition at 90 days, expiration at 7 years

- **DynamoDB:**
  - Encryption at rest (AWS managed)
  - TTL enabled for automatic cleanup after 7 years
  - Point-in-time recovery enabled

- **Lambda:**
  - Environment variables for configuration
  - CloudWatch Logs for audit logging

## Outputs

After deployment, Terraform provides the following outputs:

- `s3_bucket_name` - Name of the created S3 bucket
- `dynamodb_table_name` - Name of the DynamoDB table
- `lambda_function_name` - Name of the Lambda function
- `lambda_function_arn` - ARN of the Lambda function
- `eventbridge_rule_name` - Name of the EventBridge rule
- `deployment_summary` - Summary of all deployed resources

## Destroying Infrastructure

To remove all created resources:

```bash
terraform destroy
```

**Warning:** This will delete all data including S3 objects and DynamoDB records.

## State Management

For production deployments, configure a remote backend for state management:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "axentra-webhook-ingestion/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

## Migrating from Shell Scripts

If you previously deployed using the shell scripts in the `infrastructure/` directory:

1. Import existing resources into Terraform state
2. Or clean up existing resources before applying Terraform

See the main project [README.md](../README.md) for more information.
