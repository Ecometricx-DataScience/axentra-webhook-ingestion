#!/bin/bash
# Setup S3 bucket for processed/stripped webhook payload storage
# This script creates the S3 bucket with versioning, encryption, and lifecycle policies

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
BUCKET_NAME="axentra-webhook-processed"

echo "Setting up S3 bucket: ${BUCKET_NAME} in region: ${REGION}"

# Create S3 bucket
echo "Creating S3 bucket..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "Bucket ${BUCKET_NAME} already exists"
else
    if [ "${REGION}" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${REGION}"
    else
        aws s3api create-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${REGION}" \
            --create-bucket-configuration LocationConstraint="${REGION}"
    fi
    echo "Bucket ${BUCKET_NAME} created"
fi

# Enable versioning
echo "Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket "${BUCKET_NAME}" \
    --versioning-configuration Status=Enabled

# Block public access
echo "Blocking public access..."
aws s3api put-public-access-block \
    --bucket "${BUCKET_NAME}" \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable server-side encryption
echo "Enabling server-side encryption..."
aws s3api put-bucket-encryption \
    --bucket "${BUCKET_NAME}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

# Create lifecycle policy (shorter retention for processed data)
echo "Creating lifecycle policy..."
cat > /tmp/lifecycle-policy-processed.json <<EOF
{
    "Rules": [
        {
            "ID": "TransitionToGlacierAndDelete",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ],
            "Expiration": {
                "Days": 2555
            }
        }
    ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket "${BUCKET_NAME}" \
    --lifecycle-configuration file:///tmp/lifecycle-policy-processed.json

rm /tmp/lifecycle-policy-processed.json

# Add tags
echo "Adding tags to bucket..."
aws s3api put-bucket-tagging \
    --bucket "${BUCKET_NAME}" \
    --tagging 'TagSet=[{Key=Project,Value=Axentra Health},{Key=Environment,Value=Production},{Key=ManagedBy,Value=CLI},{Key=Purpose,Value=Webhook Processed Data}]'

echo "S3 bucket setup complete!"
echo "Bucket name: ${BUCKET_NAME}"
echo "Region: ${REGION}"

