# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., Production, Development)"
  type        = string
  default     = "Production"
}

variable "project_name" {
  description = "Project name prefix for resource naming"
  type        = string
  default     = "axentra-webhook"
}

# -----------------------------------------------------------------------------
# S3 Configuration
# -----------------------------------------------------------------------------

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for raw audit storage"
  type        = string
  default     = "axentra-webhook-raw-audit"
}

variable "s3_glacier_transition_days" {
  description = "Number of days before transitioning objects to Glacier"
  type        = number
  default     = 90
}

variable "s3_expiration_days" {
  description = "Number of days before object expiration (7 years for HIPAA compliance)"
  type        = number
  default     = 2555
}

# -----------------------------------------------------------------------------
# DynamoDB Configuration
# -----------------------------------------------------------------------------

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for event registry"
  type        = string
  default     = "axentra-webhook-events"
}

# -----------------------------------------------------------------------------
# Lambda Configuration
# -----------------------------------------------------------------------------

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "axentra-webhook-processor"
}

variable "lambda_runtime" {
  description = "Lambda runtime environment"
  type        = string
  default     = "python3.13"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "event_version" {
  description = "Event version for payload enrichment"
  type        = string
  default     = "1.0"
}

# -----------------------------------------------------------------------------
# EventBridge Configuration
# -----------------------------------------------------------------------------

variable "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  type        = string
  default     = "axentra-webhook-rule"
}

variable "eventbridge_connection_name" {
  description = "Name of the EventBridge connection"
  type        = string
  default     = "axentra-webhook-connection"
}

variable "eventbridge_api_destination_name" {
  description = "Name of the EventBridge API destination"
  type        = string
  default     = "axentra-webhook-endpoint"
}

variable "webhook_api_key" {
  description = "API key for webhook authentication (sensitive)"
  type        = string
  default     = "PLACEHOLDER_UPDATE_WITH_ACTUAL_KEY"
  sensitive   = true
}

variable "webhook_endpoint_url" {
  description = "Webhook endpoint URL for API destination"
  type        = string
  default     = "https://PLACEHOLDER_UPDATE_WITH_SUPABASE_WEBHOOK_URL"
}

variable "api_invocation_rate_limit" {
  description = "Rate limit for API invocations per second"
  type        = number
  default     = 10
}

# -----------------------------------------------------------------------------
# Data Engineer Role Configuration
# -----------------------------------------------------------------------------

variable "data_engineer_users" {
  description = "List of IAM usernames that can assume the data engineer role"
  type        = list(string)
  default = [
    "Alex.Ledbetter",
    "catalin",
    "conrad",
    "Benjamin-Westrich"
  ]
}
