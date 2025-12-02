#!/bin/bash
# Setup EventBridge API destination and rule for webhook ingestion
# This script creates the EventBridge components for receiving webhooks

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
API_DESTINATION_NAME="axentra-webhook-endpoint"
CONNECTION_NAME="axentra-webhook-connection"
RULE_NAME="axentra-webhook-rule"
LAMBDA_FUNCTION_NAME="axentra-webhook-processor"
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}"

echo "Setting up EventBridge for webhook ingestion"

# Note: API destinations require a connection with authentication
# For now, we'll create a basic setup. The actual webhook endpoint URL
# and authentication details will need to be configured based on Supabase requirements.

echo "Creating EventBridge connection..."
# Check if connection already exists
if aws events describe-connection --name "${CONNECTION_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Connection ${CONNECTION_NAME} already exists"
else
    # Create connection with API key authentication (placeholder)
    # In production, this should use the actual Supabase webhook authentication
    echo "Creating connection (using placeholder auth - update with actual Supabase credentials)..."
    aws events create-connection \
        --name "${CONNECTION_NAME}" \
        --description "Connection for Axentra webhook ingestion from Supabase" \
        --authorization-type API_KEY \
        --auth-parameters "{
            \"ApiKeyAuthParameters\": {
                \"ApiKeyName\": \"x-api-key\",
                \"ApiKeyValue\": \"PLACEHOLDER_UPDATE_WITH_ACTUAL_KEY\"
            }
        }" \
        --region "${REGION}" || echo "Note: Connection creation may require manual configuration"
fi

# Get connection ARN
CONNECTION_ARN=$(aws events describe-connection --name "${CONNECTION_NAME}" --region "${REGION}" --query 'ConnectionArn' --output text 2>/dev/null || echo "")

if [ -z "${CONNECTION_ARN}" ]; then
    echo "Warning: Could not retrieve connection ARN. API destination setup may need manual configuration."
    echo "Please create the API destination manually with the correct connection ARN."
else
    echo "Creating API destination..."
    # Check if API destination already exists
    if aws events describe-api-destination --name "${API_DESTINATION_NAME}" --region "${REGION}" 2>/dev/null; then
        echo "API destination ${API_DESTINATION_NAME} already exists"
    else
        # Note: The endpoint URL should be the actual Supabase webhook URL
        # This is a placeholder - update with actual endpoint
        aws events create-api-destination \
            --name "${API_DESTINATION_NAME}" \
            --description "API destination for Axentra webhooks" \
            --connection-arn "${CONNECTION_ARN}" \
            --invocation-endpoint "https://PLACEHOLDER_UPDATE_WITH_SUPABASE_WEBHOOK_URL" \
            --http-method POST \
            --invocation-rate-limit-per-second 10 \
            --region "${REGION}" || echo "Note: API destination creation may require actual endpoint URL"
    fi
fi

# Create EventBridge rule to route events to Lambda
echo "Creating EventBridge rule..."
if aws events describe-rule --name "${RULE_NAME}" --region "${REGION}" 2>/dev/null; then
    echo "Rule ${RULE_NAME} already exists"
else
    aws events put-rule \
        --name "${RULE_NAME}" \
        --description "Route Axentra webhook events to Lambda processor" \
        --event-pattern '{
            "source": ["axentra.webhook"],
            "detail-type": ["Axentra Webhook Event"]
        }' \
        --region "${REGION}"
    
    echo "Rule ${RULE_NAME} created"
fi

# Add Lambda as target
echo "Adding Lambda function as target..."
aws events put-targets \
    --rule "${RULE_NAME}" \
    --targets "Id=1,Arn=${LAMBDA_ARN}" \
    --region "${REGION}"

# Grant EventBridge permission to invoke Lambda
echo "Granting EventBridge permission to invoke Lambda..."
aws lambda add-permission \
    --function-name "${LAMBDA_FUNCTION_NAME}" \
    --statement-id "eventbridge-invoke-${RULE_NAME}" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/${RULE_NAME}" \
    --region "${REGION}" 2>/dev/null || echo "Permission may already exist"

echo "EventBridge setup complete!"
echo "Rule name: ${RULE_NAME}"
echo "Note: Update API destination endpoint and authentication with actual Supabase webhook details"




