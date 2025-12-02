# -----------------------------------------------------------------------------
# IAM Group for Axentra Data Engineers
# Provides direct permissions without needing to assume a role
# Users in this group automatically have access when authenticated
# -----------------------------------------------------------------------------

# Data Engineer IAM Group
resource "aws_iam_group" "data_engineer" {
  name = "axentra-data-engineer"
  path = "/axentra/"
}

# Add users to the group
resource "aws_iam_group_membership" "data_engineer" {
  name  = "axentra-data-engineer-membership"
  group = aws_iam_group.data_engineer.name
  users = var.data_engineer_users
}

# -----------------------------------------------------------------------------
# IAM Policies attached to the group
# -----------------------------------------------------------------------------

# Policy for IAM role management (create Lambda execution roles)
resource "aws_iam_group_policy" "data_engineer_iam" {
  name  = "axentra-data-engineer-iam-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "IAMRoleManagement"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:UpdateRole",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListRoleTags"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/axentra-*"
      },
      {
        Sid    = "IAMPolicyManagement"
        Effect = "Allow"
        Action = [
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/axentra-*"
      },
      {
        Sid    = "IAMPassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/axentra-*"
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "lambda.amazonaws.com"
          }
        }
      },
      {
        Sid    = "AttachAWSManagedPolicies"
        Effect = "Allow"
        Action = [
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy"
        ]
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/axentra-*"
        Condition = {
          ArnLike = {
            "iam:PolicyARN" = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
          }
        }
      }
    ]
  })
}

# Policy for Lambda function management
resource "aws_iam_group_policy" "data_engineer_lambda" {
  name  = "axentra-data-engineer-lambda-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaFunctionManagement"
        Effect = "Allow"
        Action = [
          "lambda:CreateFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:DeleteFunction",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:ListFunctions",
          "lambda:InvokeFunction",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:GetPolicy",
          "lambda:TagResource",
          "lambda:UntagResource",
          "lambda:ListTags"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:axentra-*"
      },
      {
        Sid    = "LambdaListAll"
        Effect = "Allow"
        Action = [
          "lambda:ListFunctions"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for S3 bucket access (read/write to audit bucket)
resource "aws_iam_group_policy" "data_engineer_s3" {
  name  = "axentra-data-engineer-s3-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning"
        ]
        Resource = [
          aws_s3_bucket.raw_audit.arn,
          "${aws_s3_bucket.raw_audit.arn}/*"
        ]
      }
    ]
  })
}

# Policy for DynamoDB access
resource "aws_iam_group_policy" "data_engineer_dynamodb" {
  name  = "axentra-data-engineer-dynamodb-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable"
        ]
        Resource = aws_dynamodb_table.event_registry.arn
      }
    ]
  })
}

# Policy for CloudWatch Logs access
resource "aws_iam_group_policy" "data_engineer_cloudwatch" {
  name  = "axentra-data-engineer-cloudwatch-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/axentra-*"
      },
      {
        Sid    = "CloudWatchLogsDescribe"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for EventBridge access (to view and test rules)
resource "aws_iam_group_policy" "data_engineer_eventbridge" {
  name  = "axentra-data-engineer-eventbridge-policy"
  group = aws_iam_group.data_engineer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EventBridgeAccess"
        Effect = "Allow"
        Action = [
          "events:DescribeRule",
          "events:ListRules",
          "events:ListTargetsByRule",
          "events:PutEvents"
        ]
        Resource = "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/axentra-*"
      },
      {
        Sid    = "EventBridgeList"
        Effect = "Allow"
        Action = [
          "events:ListRules"
        ]
        Resource = "*"
      }
    ]
  })
}
