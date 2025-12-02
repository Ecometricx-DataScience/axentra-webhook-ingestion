# -----------------------------------------------------------------------------
# EventBridge Configuration for Webhook Ingestion
# API destination, connection, and rule to route events to Lambda
# -----------------------------------------------------------------------------

# EventBridge connection with API key authentication
resource "aws_cloudwatch_event_connection" "webhook" {
  name               = var.eventbridge_connection_name
  description        = "Connection for Axentra webhook ingestion from Supabase"
  authorization_type = "API_KEY"

  auth_parameters {
    api_key {
      key   = "x-api-key"
      value = var.webhook_api_key
    }
  }
}

# EventBridge API destination (only created if a valid URL is provided, not a placeholder)
resource "aws_cloudwatch_event_api_destination" "webhook" {
  count = !can(regex("PLACEHOLDER", var.webhook_endpoint_url)) && can(regex("^https://", var.webhook_endpoint_url)) ? 1 : 0

  name                             = var.eventbridge_api_destination_name
  description                      = "API destination for Axentra webhooks"
  invocation_endpoint              = var.webhook_endpoint_url
  http_method                      = "POST"
  invocation_rate_limit_per_second = var.api_invocation_rate_limit
  connection_arn                   = aws_cloudwatch_event_connection.webhook.arn
}

# EventBridge rule to route webhook events to Lambda
resource "aws_cloudwatch_event_rule" "webhook" {
  name        = var.eventbridge_rule_name
  description = "Route Axentra webhook events to Lambda processor"

  event_pattern = jsonencode({
    source      = ["axentra.webhook"]
    detail-type = ["Axentra Webhook Event"]
  })

  tags = {
    Name    = var.eventbridge_rule_name
    Purpose = "Webhook event routing"
  }
}

# EventBridge target - Lambda function
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.webhook.name
  target_id = "webhook-processor-lambda"
  arn       = aws_lambda_function.webhook_processor.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "eventbridge-invoke-${var.eventbridge_rule_name}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.webhook.arn
}
