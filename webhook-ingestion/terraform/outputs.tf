# -----------------------------------------------------------------------------
# Terraform Outputs
# -----------------------------------------------------------------------------

# S3 Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for raw audit storage"
  value       = aws_s3_bucket.raw_audit.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.raw_audit.arn
}

# DynamoDB Outputs
output "dynamodb_table_name" {
  description = "Name of the DynamoDB event registry table"
  value       = aws_dynamodb_table.event_registry.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.event_registry.arn
}

# IAM Outputs
output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

# Lambda Outputs
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.webhook_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.webhook_processor.arn
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.webhook_processor.invoke_arn
}

# EventBridge Outputs
output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.webhook.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.webhook.arn
}

output "eventbridge_connection_name" {
  description = "Name of the EventBridge connection"
  value       = aws_cloudwatch_event_connection.webhook.name
}

output "eventbridge_api_destination_arn" {
  description = "ARN of the EventBridge API destination (null if not created)"
  value       = length(aws_cloudwatch_event_api_destination.webhook) > 0 ? aws_cloudwatch_event_api_destination.webhook[0].arn : null
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

# Data Engineer Group Outputs
output "data_engineer_group_name" {
  description = "Name of the data engineer IAM group"
  value       = aws_iam_group.data_engineer.name
}

output "data_engineer_group_arn" {
  description = "ARN of the data engineer IAM group"
  value       = aws_iam_group.data_engineer.arn
}

output "data_engineer_members" {
  description = "List of users in the data engineer group"
  value       = var.data_engineer_users
}

# Summary Output
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    s3_bucket            = aws_s3_bucket.raw_audit.id
    dynamodb_table       = aws_dynamodb_table.event_registry.name
    lambda_function      = aws_lambda_function.webhook_processor.function_name
    eventbridge_rule     = aws_cloudwatch_event_rule.webhook.name
    data_engineer_group  = aws_iam_group.data_engineer.name
    region               = var.aws_region
  }
}
