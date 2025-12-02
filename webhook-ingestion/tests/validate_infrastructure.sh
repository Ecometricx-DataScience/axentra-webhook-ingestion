#!/bin/bash
# Validate infrastructure scripts and configurations
# This script checks for syntax errors and validates configuration files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_DIR}/infrastructure"
CONFIG_DIR="${PROJECT_DIR}/config"
LAMBDA_DIR="${PROJECT_DIR}/lambda"

echo "=========================================="
echo "Infrastructure Validation"
echo "=========================================="
echo ""

# Check bash script syntax
echo "Checking bash script syntax..."
for script in "${INFRA_DIR}"/*.sh; do
    if [ -f "$script" ]; then
        echo "  Checking $(basename $script)..."
        bash -n "$script" && echo "    ✅ Syntax OK" || (echo "    ❌ Syntax error" && exit 1)
    fi
done
echo ""

# Check JSON configuration files
echo "Checking JSON configuration files..."
for json_file in "${CONFIG_DIR}"/*.json; do
    if [ -f "$json_file" ]; then
        echo "  Checking $(basename $json_file)..."
        python3 -m json.tool "$json_file" > /dev/null && echo "    ✅ Valid JSON" || (echo "    ❌ Invalid JSON" && exit 1)
    fi
done
echo ""

# Check Python syntax
echo "Checking Python syntax..."
if [ -f "${LAMBDA_DIR}/webhook_processor.py" ]; then
    echo "  Checking webhook_processor.py..."
    python3 -m py_compile "${LAMBDA_DIR}/webhook_processor.py" && echo "    ✅ Syntax OK" || (echo "    ❌ Syntax error" && exit 1)
fi
echo ""

# Check that required files exist
echo "Checking required files exist..."
required_files=(
    "${INFRA_DIR}/setup-s3-bucket.sh"
    "${INFRA_DIR}/setup-dynamodb.sh"
    "${INFRA_DIR}/setup-iam-role.sh"
    "${INFRA_DIR}/setup-lambda.sh"
    "${INFRA_DIR}/setup-eventbridge.sh"
    "${INFRA_DIR}/setup-infrastructure.sh"
    "${CONFIG_DIR}/lambda-trust-policy.json"
    "${CONFIG_DIR}/lambda-permissions-policy.json"
    "${LAMBDA_DIR}/webhook_processor.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $(basename $file)"
    else
        echo "  ❌ Missing: $(basename $file)"
        exit 1
    fi
done
echo ""

# Check environment variable references
echo "Checking environment variable usage..."
if grep -q "S3_RAW_AUDIT_BUCKET" "${LAMBDA_DIR}/webhook_processor.py" && \
   grep -q "DYNAMODB_TABLE_NAME" "${LAMBDA_DIR}/webhook_processor.py"; then
    echo "  ✅ Environment variables referenced correctly"
else
    echo "  ❌ Missing environment variable references"
    exit 1
fi
echo ""

# Check S3 bucket name consistency
echo "Checking S3 bucket name consistency..."
bucket_name="axentra-webhook-raw-audit"
if grep -q "${bucket_name}" "${INFRA_DIR}/setup-s3-bucket.sh" && \
   grep -q "${bucket_name}" "${INFRA_DIR}/setup-lambda.sh" && \
   grep -q "${bucket_name}" "${CONFIG_DIR}/lambda-permissions-policy.json"; then
    echo "  ✅ S3 bucket name consistent across files"
else
    echo "  ⚠️  S3 bucket name may be inconsistent"
fi
echo ""

echo "=========================================="
echo "✅ All validation checks passed!"
echo "=========================================="


