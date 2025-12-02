# -----------------------------------------------------------------------------
# Lambda Function for Webhook Processing
# Processes webhook events, strips fields, stores to S3, and registers in DynamoDB
# -----------------------------------------------------------------------------

# Create deployment package from Lambda source code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/files/webhook-processor.zip"
  excludes    = ["*.pyc", "__pycache__"]
}

# Lambda function
resource "aws_lambda_function" "webhook_processor" {
  function_name = var.lambda_function_name
  description   = "Process webhook events from Axentra Health, strip fields, and store in S3"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  role    = aws_iam_role.lambda_execution.arn
  handler = "webhook_processor.lambda_handler"
  runtime = var.lambda_runtime

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  environment {
    variables = {
      S3_RAW_AUDIT_BUCKET = aws_s3_bucket.raw_audit.id
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.event_registry.name
      EVENT_VERSION       = var.event_version
    }
  }

  tags = {
    Name       = var.lambda_function_name
    Purpose    = "Webhook event processing"
    Compliance = "HIPAA"
  }

  depends_on = [
    aws_iam_role_policy.lambda_permissions,
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 30

  tags = {
    Name    = "${var.lambda_function_name}-logs"
    Purpose = "Lambda function logs"
  }
}
