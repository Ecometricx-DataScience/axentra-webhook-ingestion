#!/bin/bash
# Setup Lambda function for webhook processing
# This script packages and deploys the Lambda function

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="axentra-webhook-processor"
RUNTIME="python3.13"
HANDLER="webhook_processor.lambda_handler"
TIMEOUT=60
MEMORY_SIZE=256
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="$(cd "${SCRIPT_DIR}/../lambda" && pwd)"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="axentra-webhook-processor-role"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
S3_RAW_BUCKET="axentra-webhook-raw-audit"
S3_PROCESSED_BUCKET="axentra-webhook-processed"
DYNAMODB_TABLE="axentra-webhook-events"

echo "Setting up Lambda function: ${FUNCTION_NAME}"

# Create deployment package
echo "Creating deployment package..."
cd "${LAMBDA_DIR}"
zip -q -r /tmp/webhook-processor.zip . -x "*.pyc" "__pycache__/*" "*.zip"

# Check if function already exists
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "${FUNCTION_NAME}" \
        --zip-file "fileb:///tmp/webhook-processor.zip" \
        --region "${REGION}"
    
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "${FUNCTION_NAME}" \
        --timeout "${TIMEOUT}" \
        --memory-size "${MEMORY_SIZE}" \
        --environment "Variables={
            S3_RAW_AUDIT_BUCKET=${S3_RAW_BUCKET},
            S3_PROCESSED_BUCKET=${S3_PROCESSED_BUCKET},
            DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE},
            EVENT_VERSION=1.0
        }" \
        --region "${REGION}"
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name "${FUNCTION_NAME}" \
        --runtime "${RUNTIME}" \
        --role "${ROLE_ARN}" \
        --handler "${HANDLER}" \
        --zip-file "fileb:///tmp/webhook-processor.zip" \
        --timeout "${TIMEOUT}" \
        --memory-size "${MEMORY_SIZE}" \
        --description "Process webhook events from Axentra Health, strip fields, and store in S3" \
        --environment "Variables={
            S3_RAW_AUDIT_BUCKET=${S3_RAW_BUCKET},
            S3_PROCESSED_BUCKET=${S3_PROCESSED_BUCKET},
            DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE},
            EVENT_VERSION=1.0
        }" \
        --region "${REGION}" \
        --tags "Project=AxentraWebhookIngestion,Environment=Production"
    
    echo "Waiting for function to be active..."
    aws lambda wait function-active \
        --function-name "${FUNCTION_NAME}" \
        --region "${REGION}"
fi

# Clean up
rm -f /tmp/webhook-processor.zip

echo "Lambda function setup complete!"
echo "Function name: ${FUNCTION_NAME}"
echo "Function ARN: $(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${REGION} --query 'Configuration.FunctionArn' --output text)"

