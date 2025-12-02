#!/bin/bash
# Cleanup script for Axentra Webhook Ingestion System
# This script removes all created AWS resources

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
BUCKET_NAME="axentra-webhook-raw-audit"
TABLE_NAME="axentra-webhook-events"
ROLE_NAME="axentra-webhook-processor-role"
FUNCTION_NAME="axentra-webhook-processor"
RULE_NAME="axentra-webhook-rule"
API_DESTINATION_NAME="axentra-webhook-endpoint"
CONNECTION_NAME="axentra-webhook-connection"
POLICY_NAME="axentra-webhook-processor-policy"

echo "=========================================="
echo "Cleaning up Axentra Webhook Ingestion System"
echo "=========================================="
echo ""

# Confirm deletion
read -p "Are you sure you want to delete all resources? (yes/no): " confirm
if [ "${confirm}" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Step 1: Remove EventBridge targets and rule
echo "Step 1/7: Removing EventBridge targets and rule..."
if aws events describe-rule --name "${RULE_NAME}" --region "${REGION}" 2>/dev/null; then
    # Remove all targets
    aws events remove-targets \
        --rule "${RULE_NAME}" \
        --ids "1" \
        --region "${REGION}" 2>/dev/null || true
    
    # Delete rule
    aws events delete-rule \
        --name "${RULE_NAME}" \
        --region "${REGION}"
    echo "EventBridge rule removed"
else
    echo "EventBridge rule not found"
fi
echo ""

# Step 2: Remove API destination
echo "Step 2/7: Removing EventBridge API destination..."
if aws events describe-api-destination --name "${API_DESTINATION_NAME}" --region "${REGION}" 2>/dev/null; then
    aws events delete-api-destination \
        --name "${API_DESTINATION_NAME}" \
        --region "${REGION}"
    echo "API destination removed"
else
    echo "API destination not found"
fi
echo ""

# Step 3: Remove connection
echo "Step 3/7: Removing EventBridge connection..."
if aws events describe-connection --name "${CONNECTION_NAME}" --region "${REGION}" 2>/dev/null; then
    aws events delete-connection \
        --name "${CONNECTION_NAME}" \
        --region "${REGION}"
    echo "Connection removed"
else
    echo "Connection not found"
fi
echo ""

# Step 4: Remove Lambda function
echo "Step 4/7: Removing Lambda function..."
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" 2>/dev/null; then
    aws lambda delete-function \
        --function-name "${FUNCTION_NAME}" \
        --region "${REGION}"
    echo "Lambda function removed"
else
    echo "Lambda function not found"
fi
echo ""

# Step 5: Remove IAM role and policies
echo "Step 5/7: Removing IAM role and policies..."
if aws iam get-role --role-name "${ROLE_NAME}" --region "${REGION}" 2>/dev/null; then
    # Detach managed policy
    aws iam detach-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
        2>/dev/null || true
    
    # Delete inline policy
    aws iam delete-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name "${POLICY_NAME}" \
        2>/dev/null || true
    
    # Delete role
    aws iam delete-role \
        --role-name "${ROLE_NAME}"
    echo "IAM role removed"
else
    echo "IAM role not found"
fi
echo ""

# Step 6: Remove DynamoDB table
echo "Step 6/7: Removing DynamoDB table..."
if aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${REGION}" 2>/dev/null; then
    aws dynamodb delete-table \
        --table-name "${TABLE_NAME}" \
        --region "${REGION}"
    
    echo "Waiting for table deletion..."
    aws dynamodb wait table-not-exists \
        --table-name "${TABLE_NAME}" \
        --region "${REGION}"
    echo "DynamoDB table removed"
else
    echo "DynamoDB table not found"
fi
echo ""

# Step 7: Remove S3 bucket (with all objects and versions)
echo "Step 7/7: Removing S3 bucket..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "Warning: This will delete all objects and versions in the bucket."
    read -p "Continue with S3 bucket deletion? (yes/no): " confirm_bucket
    if [ "${confirm_bucket}" = "yes" ]; then
        # Delete all object versions
        aws s3api delete-objects \
            --bucket "${BUCKET_NAME}" \
            --delete "$(aws s3api list-object-versions \
                --bucket "${BUCKET_NAME}" \
                --output json \
                --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" \
            2>/dev/null || true
        
        # Delete all delete markers
        aws s3api delete-objects \
            --bucket "${BUCKET_NAME}" \
            --delete "$(aws s3api list-object-versions \
                --bucket "${BUCKET_NAME}" \
                --output json \
                --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')" \
            2>/dev/null || true
        
        # Delete bucket
        aws s3api delete-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${REGION}"
        echo "S3 bucket removed"
    else
        echo "S3 bucket deletion skipped"
    fi
else
    echo "S3 bucket not found"
fi
echo ""

echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="

