#!/bin/bash
# Setup DynamoDB table for event registry
# This script creates the DynamoDB table with proper schema and TTL

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
TABLE_NAME="axentra-webhook-events"

echo "Setting up DynamoDB table: ${TABLE_NAME} in region: ${REGION}"

# Check if table already exists
if aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Table ${TABLE_NAME} already exists"
else
    echo "Creating DynamoDB table..."
    aws dynamodb create-table \
        --table-name "${TABLE_NAME}" \
        --attribute-definitions \
            AttributeName=payload_hash,AttributeType=S \
            AttributeName=processing_timestamp,AttributeType=S \
        --key-schema \
            AttributeName=payload_hash,KeyType=HASH \
            AttributeName=processing_timestamp,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "${REGION}" \
        --tags \
            Key=Project,Value="Axentra Health" \
            Key=Environment,Value=Production \
            Key=ManagedBy,Value=CLI \
            Key=Purpose,Value=Webhook Event Registry

    echo "Waiting for table to be active..."
    aws dynamodb wait table-exists \
        --table-name "${TABLE_NAME}" \
        --region "${REGION}"

    echo "DynamoDB table created successfully"
fi

# Enable TTL on the table
echo "Enabling TTL on table..."
aws dynamodb update-time-to-live \
    --table-name "${TABLE_NAME}" \
    --time-to-live-specification \
        Enabled=true,AttributeName=ttl \
    --region "${REGION}"

echo "DynamoDB table setup complete!"
echo "Table name: ${TABLE_NAME}"
echo "Region: ${REGION}"




