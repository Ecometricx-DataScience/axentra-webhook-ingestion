#!/bin/bash
# Main infrastructure setup script for Axentra Webhook Ingestion System
# This script orchestrates the creation of all AWS resources

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION=${AWS_REGION:-us-east-1}

echo "=========================================="
echo "Axentra Webhook Ingestion System Setup"
echo "=========================================="
echo "Region: ${REGION}"
echo ""

# Make all scripts executable
chmod +x "${SCRIPT_DIR}"/*.sh

# Step 1: Setup S3 bucket
echo "Step 1/6: Setting up S3 bucket..."
"${SCRIPT_DIR}/setup-s3-bucket.sh"
echo ""

# Step 2: Setup DynamoDB table
echo "Step 2/6: Setting up DynamoDB table..."
"${SCRIPT_DIR}/setup-dynamodb.sh"
echo ""

# Step 3: Setup IAM role
echo "Step 3/6: Setting up IAM role..."
"${SCRIPT_DIR}/setup-iam-role.sh"
echo ""

# Step 4: Setup Lambda function
echo "Step 4/6: Setting up Lambda function..."
"${SCRIPT_DIR}/setup-lambda.sh"
echo ""

# Step 5: Setup EventBridge
echo "Step 5/6: Setting up EventBridge..."
"${SCRIPT_DIR}/setup-eventbridge.sh"
echo ""

# Step 6: Summary
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Created Resources:"
echo "  - S3 Bucket: axentra-webhook-raw-audit"
echo "  - DynamoDB Table: axentra-webhook-events"
echo "  - IAM Role: axentra-webhook-processor-role"
echo "  - Lambda Function: axentra-webhook-processor"
echo "  - EventBridge Rule: axentra-webhook-rule"
echo ""
echo "Next Steps:"
echo "  1. Update EventBridge API destination with actual Supabase webhook URL"
echo "  2. Update EventBridge connection with actual authentication credentials"
echo "  3. Test the webhook endpoint with a sample payload"
echo "  4. Configure downstream routing targets"
echo ""
echo "To clean up all resources, run:"
echo "  ${SCRIPT_DIR}/cleanup-infrastructure.sh"
echo ""

