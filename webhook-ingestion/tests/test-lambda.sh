#!/bin/bash
# Test Lambda function with curl/Postman-style requests
# This script provides multiple ways to test the Lambda function

set -e

REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="axentra-webhook-processor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD_FILE="${SCRIPT_DIR}/test-payload.json"

echo "=========================================="
echo "Lambda Function Testing"
echo "=========================================="
echo ""

# Method 1: Direct Lambda Invocation (AWS CLI)
echo "Method 1: Direct Lambda Invocation (AWS CLI)"
echo "--------------------------------------------"
echo "Invoking Lambda function directly..."
echo ""

aws lambda invoke \
  --function-name "${FUNCTION_NAME}" \
  --payload "file://${PAYLOAD_FILE}" \
  --region "${REGION}" \
  "${SCRIPT_DIR}/response.json" \
  --cli-binary-format raw-in-base64-out

echo "Response:"
cat "${SCRIPT_DIR}/response.json" | jq '.' 2>/dev/null || cat "${SCRIPT_DIR}/response.json"
echo ""
echo ""

# Method 2: Using curl with AWS CLI (for API Gateway if configured)
echo "Method 2: Testing with sample payload"
echo "--------------------------------------------"
echo "Payload being sent:"
cat "${PAYLOAD_FILE}" | jq '.' 2>/dev/null || cat "${PAYLOAD_FILE}"
echo ""
echo ""

# Method 3: Show how to test with Postman
echo "Method 3: Postman/curl Instructions"
echo "--------------------------------------------"
echo "To test with Postman or curl, you can:"
echo ""
echo "1. Use AWS CLI to invoke Lambda:"
echo "   aws lambda invoke \\"
echo "     --function-name ${FUNCTION_NAME} \\"
echo "     --payload file://test-payload.json \\"
echo "     --region ${REGION} \\"
echo "     response.json"
echo ""
echo "2. Or use AWS CLI with inline JSON:"
echo "   aws lambda invoke \\"
echo "     --function-name ${FUNCTION_NAME} \\"
echo "     --payload '{\"event_type\":\"new_product\",\"products\":{\"name\":\"Test\"}}' \\"
echo "     --region ${REGION} \\"
echo "     response.json"
echo ""
echo "3. To test with different payloads, modify test-payload.json"
echo ""

# Show CloudWatch logs
echo "=========================================="
echo "Recent CloudWatch Logs"
echo "=========================================="
echo "Fetching recent logs..."
echo ""

LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"
if aws logs describe-log-groups --log-group-name-prefix "${LOG_GROUP}" --region "${REGION}" 2>/dev/null | grep -q "${LOG_GROUP}"; then
    aws logs tail "${LOG_GROUP}" --region "${REGION}" --since 5m --format short 2>/dev/null || echo "No recent logs found"
else
    echo "Log group not found yet. Logs will appear after first invocation."
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="

