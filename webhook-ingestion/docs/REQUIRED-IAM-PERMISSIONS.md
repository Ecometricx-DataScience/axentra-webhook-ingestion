# Required IAM Permissions for Axentra Webhook Ingestion System

## Summary

This document lists all IAM permissions required to set up and operate the Axentra Webhook Ingestion System. Some permissions were tested during setup, while others are required based on the infrastructure components.

## Permissions You Currently Have ✅

Based on successful operations during setup:

1. **S3 Operations**
   - `s3:CreateBucket` ✅
   - `s3:PutBucketVersioning` ✅
   - `s3:PutBucketEncryption` ✅
   - `s3:PutBucketLifecycleConfiguration` ✅
   - `s3:PutPublicAccessBlock` ✅
   - `s3:HeadBucket` ✅

2. **DynamoDB Operations**
   - `dynamodb:CreateTable` ✅
   - `dynamodb:DescribeTable` ✅
   - `dynamodb:UpdateTimeToLive` ✅
   - `dynamodb:Wait` ✅

3. **EventBridge Operations**
   - `events:CreateConnection` ✅
   - `events:PutRule` ✅
   - `events:PutTargets` ✅
   - `events:DescribeConnection` ✅
   - `events:DescribeRule` ✅

4. **Lambda Operations (Partial)**
   - `lambda:AddPermission` ✅ (EventBridge can invoke Lambda)
   - `lambda:GetFunction` ✅ (likely, for checking existence)

5. **Bedrock Access**
   - `bedrock:ListFoundationModels` ✅

## Permissions You Need ❌

### 1. IAM Role Creation

**Permission:** `iam:CreateRole`

**Required for:**
- Creating the `axentra-webhook-processor-role` execution role for Lambda

**Error encountered:**
```
User is not authorized to perform: iam:CreateRole on resource: 
arn:aws:iam::302146782327:role/axentra-webhook-processor-role
```

**Additional IAM permissions needed:**
- `iam:GetRole` - To check if role exists (optional but helpful)
- `iam:TagRole` - To add tags to the role (optional)

### 2. IAM PassRole

**Permission:** `iam:PassRole`

**Required for:**
- Assigning the execution role to the Lambda function
- This is required even if the role already exists

**Error encountered:**
```
User is not authorized to perform: iam:PassRole on resource: 
arn:aws:iam::302146782327:role/axentra-webhook-processor-role
```

**Note:** This permission must specify the role ARN or use a wildcard pattern.

### 3. IAM Policy Management

**Permission:** `iam:PutRolePolicy`

**Required for:**
- Attaching inline policies to the Lambda execution role
- Setting up the custom permissions policy

**Also needed:**
- `iam:GetRolePolicy` - To check existing policies (optional)
- `iam:DeleteRolePolicy` - To update/replace policies (optional)

### 4. IAM Managed Policy Attachment

**Permission:** `iam:AttachRolePolicy`

**Required for:**
- Attaching AWS managed policies (e.g., `AWSLambdaBasicExecutionRole`)
- This is different from inline policies

**Also needed:**
- `iam:DetachRolePolicy` - To remove policies if needed (optional)
- `iam:ListAttachedRolePolicies` - To check attached policies (optional)

### 5. Lambda Function Creation

**Permission:** `lambda:CreateFunction`

**Required for:**
- Creating the `axentra-webhook-processor` Lambda function

**Note:** This will fail without `iam:PassRole` permission first.

**Additional Lambda permissions needed:**
- `lambda:UpdateFunctionCode` - To update function code
- `lambda:UpdateFunctionConfiguration` - To update environment variables, timeout, etc.
- `lambda:GetFunction` - To check if function exists
- `lambda:TagResource` - To add tags to function

### 6. EventBridge API Destination (Partial)

**Permission:** `events:CreateApiDestination`

**Status:** Script attempted this but failed due to invalid placeholder URL (not a permission issue)

**Note:** Once you have a valid Supabase webhook URL, this should work with current permissions.

**Also needed:**
- `events:UpdateApiDestination` - To update endpoint URL later
- `events:DescribeApiDestination` - To check API destination status

## Complete IAM Policy for Setup

Here's a complete IAM policy that includes all required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3BucketManagement",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:PutBucketVersioning",
                "s3:PutBucketEncryption",
                "s3:PutBucketLifecycleConfiguration",
                "s3:PutPublicAccessBlock",
                "s3:HeadBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::axentra-webhook-raw-audit"
        },
        {
            "Sid": "DynamoDBTableManagement",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:UpdateTimeToLive",
                "dynamodb:Wait"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/axentra-webhook-events"
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:GetRole",
                "iam:PutRolePolicy",
                "iam:GetRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:ListAttachedRolePolicies",
                "iam:TagRole"
            ],
            "Resource": "arn:aws:iam::302146782327:role/axentra-webhook-processor-role"
        },
        {
            "Sid": "IAMPassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::302146782327:role/axentra-webhook-processor-role",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "lambda.amazonaws.com"
                }
            }
        },
        {
            "Sid": "LambdaFunctionManagement",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:TagResource"
            ],
            "Resource": "arn:aws:lambda:*:*:function:axentra-webhook-processor"
        },
        {
            "Sid": "EventBridgeManagement",
            "Effect": "Allow",
            "Action": [
                "events:CreateConnection",
                "events:CreateApiDestination",
                "events:UpdateApiDestination",
                "events:DescribeConnection",
                "events:DescribeApiDestination",
                "events:PutRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "events:DescribeRule"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:DescribeLogGroups"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/axentra-webhook-processor"
        }
    ]
}
```

## Permissions Already Listed (From Your Original List)

These were already identified and are still needed:

1. **Lambda function creation**
   - `lambda:CreateFunction` ❌ (Need)
   - `iam:PassRole` ❌ (Need)

2. **CloudWatch Logs subscription**
   - `logs:PutSubscriptionFilter` ❓ (Not tested yet - may have)

3. **Lambda invocation permission**
   - `lambda:AddPermission` ✅ (Have - EventBridge can invoke)

4. **IAM role policy**
   - `iam:AttachRolePolicy` ❌ (Need)
   - `iam:PutRolePolicy` ❌ (Need - for inline policies)

## Additional Permissions Needed (Not in Original List)

1. **IAM Role Creation**
   - `iam:CreateRole` ❌

2. **IAM Policy Management**
   - `iam:PutRolePolicy` ❌ (for inline policies)
   - `iam:GetRolePolicy` (optional)
   - `iam:DeleteRolePolicy` (optional)

3. **Lambda Updates**
   - `lambda:UpdateFunctionCode` ❌
   - `lambda:UpdateFunctionConfiguration` ❌

4. **EventBridge API Destination**
   - `events:CreateApiDestination` ✅ (Have, but needs valid URL)
   - `events:UpdateApiDestination` (for updating endpoint)

## Next Steps

1. **Request IAM Permissions:**
   - Ask your AWS administrator to grant the permissions listed above
   - The most critical ones are:
     - `iam:CreateRole`
     - `iam:PassRole`
     - `iam:PutRolePolicy`
     - `iam:AttachRolePolicy`
     - `lambda:CreateFunction`

2. **After Permissions Granted:**
   - Re-run `setup-iam-role.sh`
   - Re-run `setup-lambda.sh`
   - Update EventBridge API destination with actual Supabase webhook URL

3. **Test Permissions:**
   - Test Lambda function with sample payload
   - Verify S3 storage and DynamoDB registration
   - Test idempotency with duplicate payloads

## Current Setup Status

✅ **Completed:**
- S3 bucket created and configured
- DynamoDB table created and configured
- EventBridge connection created
- EventBridge rule created

❌ **Pending (Requires Additional Permissions):**
- IAM role creation
- Lambda function creation
- IAM policy attachment

⚠️ **Needs Configuration:**
- EventBridge API destination (needs valid Supabase webhook URL)

