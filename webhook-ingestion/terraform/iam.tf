# -----------------------------------------------------------------------------
# IAM Role and Policies for Lambda Function
# -----------------------------------------------------------------------------

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# IAM role for Lambda execution
resource "aws_iam_role" "lambda_execution" {
  name        = "${var.project_name}-processor-role"
  description = "Execution role for Axentra webhook processor Lambda function"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-processor-role"
    Purpose = "Lambda execution role for webhook processing"
  }
}

# Custom inline policy for S3, DynamoDB, and CloudWatch access
resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-processor-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3RawAuditBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.raw_audit.arn}/*"
      },
      {
        Sid    = "DynamoDBEventRegistryAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.event_registry.arn
      },
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# Attach AWS managed policy for Lambda basic execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
