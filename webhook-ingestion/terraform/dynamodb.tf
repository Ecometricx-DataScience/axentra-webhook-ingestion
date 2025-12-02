# -----------------------------------------------------------------------------
# DynamoDB Table for Event Registry
# Used for idempotency checking, event tracking, and routing configuration
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "event_registry" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"

  # Primary key: payload_hash (HASH) + processing_timestamp (RANGE)
  hash_key  = "payload_hash"
  range_key = "processing_timestamp"

  attribute {
    name = "payload_hash"
    type = "S"
  }

  attribute {
    name = "processing_timestamp"
    type = "S"
  }

  # Enable TTL for automatic cleanup after 7 years
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name       = var.dynamodb_table_name
    Purpose    = "Webhook event registry and idempotency tracking"
    Compliance = "HIPAA"
  }
}
