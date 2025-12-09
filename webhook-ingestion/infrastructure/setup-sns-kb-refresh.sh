#!/bin/bash
# Setup SNS topic for KB refresh triggers
# This script creates an SNS topic for triggering Knowledge Base refreshes

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
TOPIC_NAME="axentra-kb-refresh"

echo "Setting up SNS topic: ${TOPIC_NAME} in region: ${REGION}"

# Create SNS topic
echo "Creating SNS topic..."
if aws sns get-topic-attributes --topic-arn "arn:aws:sns:${REGION}:$(aws sts get-caller-identity --query Account --output text):${TOPIC_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Topic ${TOPIC_NAME} already exists"
    TOPIC_ARN=$(aws sns get-topic-attributes --topic-arn "arn:aws:sns:${REGION}:$(aws sts get-caller-identity --query Account --output text):${TOPIC_NAME}" --region "${REGION}" --query 'Attributes.TopicArn' --output text 2>/dev/null || aws sns list-topics --region "${REGION}" --query "Topics[?contains(TopicArn, '${TOPIC_NAME}')].TopicArn" --output text | head -1)
else
    TOPIC_ARN=$(aws sns create-topic \
        --name "${TOPIC_NAME}" \
        --region "${REGION}" \
        --query 'TopicArn' \
        --output text)
    echo "Topic ${TOPIC_NAME} created"
fi

# Tag the topic
echo "Tagging SNS topic..."
aws sns tag-resource \
    --resource-arn "${TOPIC_ARN}" \
    --tags "Key=Project,Value=Axentra Health" "Key=Environment,Value=Production" "Key=ManagedBy,Value=CLI" "Key=Purpose,Value=KB Refresh Trigger" \
    --region "${REGION}" 2>/dev/null || echo "Note: Tagging may have failed"

echo "SNS topic setup complete!"
echo "Topic ARN: ${TOPIC_ARN}"
echo "Region: ${REGION}"
echo ""
echo "To subscribe to this topic:"
echo "  aws sns subscribe --topic-arn ${TOPIC_ARN} --protocol email --notification-endpoint your-email@example.com"


