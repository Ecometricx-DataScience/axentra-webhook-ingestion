#!/bin/bash
# Script to switch AWS account credentials
# This will configure AWS CLI with the new credentials

set -e

echo "=========================================="
echo "Switching AWS Account"
echo "=========================================="
echo ""

# New credentials
# NOTE: Set these as environment variables or pass as arguments
# ACCESS_KEY_ID="${1:-$AWS_ACCESS_KEY_ID}"
# SECRET_ACCESS_KEY="${2:-$AWS_SECRET_ACCESS_KEY}"
REGION="${AWS_REGION:-us-east-1}"

# Check if credentials are provided
if [ -z "${AWS_ACCESS_KEY_ID}" ] || [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
    echo "Error: AWS credentials must be set as environment variables:"
    echo "  export AWS_ACCESS_KEY_ID=your-access-key-id"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret-access-key"
    exit 1
fi

ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"

echo "Configuring AWS CLI with new credentials..."
echo ""

# Configure AWS credentials
aws configure set aws_access_key_id "${ACCESS_KEY_ID}"
aws configure set aws_secret_access_key "${SECRET_ACCESS_KEY}"
aws configure set default.region "${REGION}"

echo "✓ AWS credentials configured"
echo ""

# Verify the account
echo "Verifying new account..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
USER_ARN=$(aws sts get-caller-identity --query Arn --output text)

echo "Account ID: ${ACCOUNT_ID}"
echo "User ARN: ${USER_ARN}"
echo "Region: ${REGION}"
echo ""

echo "=========================================="
echo "Account Switch Complete!"
echo "=========================================="
echo ""
echo "You are now using the correct AWS account."
echo "You can now run: ./setup-infrastructure.sh"


