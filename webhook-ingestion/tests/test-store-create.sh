#!/bin/bash
# Test script for store creation event with metadata storage

set -e

REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="axentra-webhook-processor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD_FILE="${SCRIPT_DIR}/test-store-create-payload.json"

echo "Testing store creation event with metadata storage..."
echo ""

# Check if Lambda function exists
if ! aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" > /dev/null 2>&1; then
    echo "❌ Lambda function ${FUNCTION_NAME} not found. Please run setup-infrastructure.sh first."
    exit 1
fi

# Check if payload file exists
if [ ! -f "${PAYLOAD_FILE}" ]; then
    echo "❌ Payload file not found: ${PAYLOAD_FILE}"
    exit 1
fi

echo "Invoking Lambda function with store creation payload..."
echo ""

# Invoke Lambda function
RESPONSE=$(aws lambda invoke \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --payload "file://${PAYLOAD_FILE}" \
    --cli-binary-format raw-in-base64-out \
    /tmp/lambda-response.json 2>&1)

if [ $? -eq 0 ]; then
    echo "✅ Lambda invocation successful!"
    echo ""
    echo "Response:"
    cat /tmp/lambda-response.json | jq '.'
    echo ""
    
    # Check if metadata_s3_key is in response
    if grep -q "metadata_s3_key" /tmp/lambda-response.json; then
        echo "✅ Metadata file was created!"
        METADATA_KEY=$(cat /tmp/lambda-response.json | jq -r '.body | fromjson | .metadata_s3_key // empty')
        if [ -n "${METADATA_KEY}" ]; then
            echo "Metadata S3 key: ${METADATA_KEY}"
            echo ""
            echo "Verifying metadata file in S3..."
            BUCKET=$(cat /tmp/lambda-response.json | jq -r '.body | fromjson | .raw_s3_key // empty' | cut -d'/' -f1)
            if [ -n "${BUCKET}" ]; then
                echo "Bucket: ${BUCKET}"
                echo "Metadata key: ${METADATA_KEY}"
                echo ""
                echo "Metadata file contents:"
                aws s3 cp "s3://${BUCKET}/${METADATA_KEY}" - 2>/dev/null | jq '.' || echo "Could not retrieve metadata file"
            fi
        fi
    else
        echo "⚠️  No metadata_s3_key in response (might not be a store_create event)"
    fi
    
    # Check if store_id was auto-generated
    STORE_ID=$(cat /tmp/lambda-response.json | jq -r '.body | fromjson | .store_id // empty')
    if [ -n "${STORE_ID}" ]; then
        echo ""
        echo "Store ID: ${STORE_ID}"
    fi
else
    echo "❌ Lambda invocation failed:"
    echo "${RESPONSE}"
    exit 1
fi

echo ""
echo "Test complete!"

