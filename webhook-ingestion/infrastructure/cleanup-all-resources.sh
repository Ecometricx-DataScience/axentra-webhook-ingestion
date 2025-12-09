#!/bin/bash
# Cleanup script to delete all Axentra webhook ingestion resources
# Use this if resources were created in the wrong AWS account

set -e

REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=========================================="
echo "Cleaning up Axentra Webhook Resources"
echo "Account: ${ACCOUNT_ID}"
echo "Region: ${REGION}"
echo "=========================================="
echo ""

# S3 Buckets
echo "Deleting S3 buckets..."
for bucket in "axentra-webhook-raw-audit" "axentra-webhook-processed"; do
    if aws s3 ls "s3://${bucket}" 2>/dev/null; then
        echo "  Deleting bucket: ${bucket}"
        # Delete all objects and versions
        aws s3 rm "s3://${bucket}" --recursive 2>/dev/null || true
        # Delete bucket
        aws s3 rb "s3://${bucket}" --force 2>/dev/null || true
        echo "  ✓ Deleted ${bucket}"
    else
        echo "  ⊘ Bucket ${bucket} does not exist"
    fi
done
echo ""

# Lambda Function
echo "Deleting Lambda function..."
if aws lambda get-function --function-name "axentra-webhook-processor" --region "${REGION}" 2>/dev/null; then
    echo "  Deleting function: axentra-webhook-processor"
    aws lambda delete-function --function-name "axentra-webhook-processor" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted Lambda function"
else
    echo "  ⊘ Lambda function does not exist"
fi
echo ""

# DynamoDB Table
echo "Deleting DynamoDB table..."
if aws dynamodb describe-table --table-name "axentra-webhook-events" --region "${REGION}" 2>/dev/null; then
    echo "  Deleting table: axentra-webhook-events"
    aws dynamodb delete-table --table-name "axentra-webhook-events" --region "${REGION}" 2>/dev/null || true
    echo "  Waiting for table deletion..."
    aws dynamodb wait table-not-exists --table-name "axentra-webhook-events" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted DynamoDB table"
else
    echo "  ⊘ DynamoDB table does not exist"
fi
echo ""

# IAM Role
echo "Deleting IAM role..."
ROLE_NAME="axentra-webhook-processor-role"
if aws iam get-role --role-name "${ROLE_NAME}" 2>/dev/null; then
    echo "  Detaching policies from role: ${ROLE_NAME}"
    # List and detach policies
    for policy in $(aws iam list-attached-role-policies --role-name "${ROLE_NAME}" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
        aws iam detach-role-policy --role-name "${ROLE_NAME}" --policy-arn "${policy}" 2>/dev/null || true
    done
    # Delete inline policies
    for policy in $(aws iam list-role-policies --role-name "${ROLE_NAME}" --query 'PolicyNames[]' --output text 2>/dev/null); do
        aws iam delete-role-policy --role-name "${ROLE_NAME}" --policy-name "${policy}" 2>/dev/null || true
    done
    # Delete role
    aws iam delete-role --role-name "${ROLE_NAME}" 2>/dev/null || true
    echo "  ✓ Deleted IAM role"
else
    echo "  ⊘ IAM role does not exist"
fi
echo ""

# EventBridge Rule
echo "Deleting EventBridge rule..."
RULE_NAME="axentra-webhook-rule"
if aws events describe-rule --name "${RULE_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "  Removing targets from rule: ${RULE_NAME}"
    aws events remove-targets --rule "${RULE_NAME}" --ids "1" --region "${REGION}" 2>/dev/null || true
    echo "  Deleting rule: ${RULE_NAME}"
    aws events delete-rule --name "${RULE_NAME}" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted EventBridge rule"
else
    echo "  ⊘ EventBridge rule does not exist"
fi
echo ""

# EventBridge API Destination
echo "Deleting EventBridge API destination..."
API_DEST_NAME="axentra-webhook-endpoint"
if aws events describe-api-destination --name "${API_DEST_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "  Deleting API destination: ${API_DEST_NAME}"
    aws events delete-api-destination --name "${API_DEST_NAME}" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted API destination"
else
    echo "  ⊘ API destination does not exist"
fi
echo ""

# EventBridge Connection
echo "Deleting EventBridge connection..."
CONN_NAME="axentra-webhook-connection"
if aws events describe-connection --name "${CONN_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "  Deleting connection: ${CONN_NAME}"
    aws events delete-connection --name "${CONN_NAME}" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted connection"
else
    echo "  ⊘ Connection does not exist"
fi
echo ""

# SNS Topic
echo "Deleting SNS topic..."
TOPIC_NAME="axentra-kb-refresh"
TOPIC_ARN="arn:aws:sns:${REGION}:${ACCOUNT_ID}:${TOPIC_NAME}"
if aws sns get-topic-attributes --topic-arn "${TOPIC_ARN}" --region "${REGION}" 2>/dev/null; then
    echo "  Deleting topic: ${TOPIC_NAME}"
    aws sns delete-topic --topic-arn "${TOPIC_ARN}" --region "${REGION}" 2>/dev/null || true
    echo "  ✓ Deleted SNS topic"
else
    echo "  ⊘ SNS topic does not exist"
fi
echo ""

echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "All Axentra webhook resources have been deleted."
echo "You can now switch to the correct AWS account."


