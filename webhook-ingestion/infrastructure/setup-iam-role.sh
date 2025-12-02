#!/bin/bash
# Setup IAM role and policies for Lambda function
# This script creates the execution role and attaches necessary policies

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
ROLE_NAME="axentra-webhook-processor-role"
POLICY_NAME="axentra-webhook-processor-policy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "${SCRIPT_DIR}/../config" && pwd)"

echo "Setting up IAM role: ${ROLE_NAME}"

# Create trust policy file path
TRUST_POLICY="${CONFIG_DIR}/lambda-trust-policy.json"
PERMISSIONS_POLICY="${CONFIG_DIR}/lambda-permissions-policy.json"

# Check if role already exists
if aws iam get-role --role-name "${ROLE_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Role ${ROLE_NAME} already exists"
else
    echo "Creating IAM role..."
    aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "file://${TRUST_POLICY}" \
        --description "Execution role for Axentra webhook processor Lambda function" \
        --tags "Key=Project,Value=Axentra Health" "Key=Environment,Value=Production" "Key=ManagedBy,Value=CLI" "Key=Purpose,Value=Lambda Execution Role"
    
    echo "Role ${ROLE_NAME} created"
fi

# Create inline policy
echo "Creating inline policy..."
aws iam put-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-name "${POLICY_NAME}" \
    --policy-document "file://${PERMISSIONS_POLICY}"

# Attach basic Lambda execution policy (for CloudWatch Logs)
echo "Attaching AWS managed policy for Lambda basic execution..."
aws iam attach-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

echo "IAM role setup complete!"
echo "Role name: ${ROLE_NAME}"
echo "Role ARN: $(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text)"




