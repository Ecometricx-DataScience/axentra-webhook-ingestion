# Your AWS Bedrock Access

## ✅ Bedrock Access Confirmed

You have full access to AWS Bedrock services!

## Available Services

### 1. Foundation Models ✅
- **Status:** Can list and access foundation models
- **Regions:** us-east-1, us-west-2
- **Access:** Full read access to model catalog

### 2. Custom Models ✅
- **Status:** Can list custom models (currently none)
- **Access:** Full access to custom model management

### 3. Bedrock Agents ✅
- **Status:** Active agents found
- **Agents:**
  - **Axentra-Agent** (ID: CZIAFQGC5O)
    - Status: PREPARED
    - Description: MED-SPA AGENT PROTOTYPE
    - Latest Version: 1
    - Updated: 2025-08-20

## Available Bedrock Operations

Based on your permissions, you can:
- ✅ List foundation models
- ✅ List custom models
- ✅ List and manage Bedrock agents
- ✅ Access model inference (likely - can test if needed)

## Common Bedrock Commands

```bash
# List all foundation models
aws bedrock list-foundation-models --region us-east-1

# List Claude models specifically
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude`)]'

# List your agents
aws bedrock-agent list-agents --region us-east-1

# Invoke a model (example)
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
  --body '{"prompt":"Hello"}' \
  --region us-east-1 \
  response.json
```

## Note

You have Bedrock access, which is separate from the IAM permissions needed for the S3 monitoring setup. The S3 monitoring still requires:
- `iam:PassRole` 
- `iam:AttachRolePolicy`
- `lambda:CreateFunction`

But if you want to use Bedrock for any part of the monitoring system (like processing alerts with AI), you have full access!


