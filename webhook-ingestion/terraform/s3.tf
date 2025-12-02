# -----------------------------------------------------------------------------
# S3 Bucket for Raw Webhook Payload Storage
# HIPAA-compliant configuration with versioning, encryption, and lifecycle policies
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "raw_audit" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = var.s3_bucket_name
    Purpose     = "Raw webhook payload audit storage"
    Compliance  = "HIPAA"
  }
}

# Enable versioning for immutable audit trail
resource "aws_s3_bucket_versioning" "raw_audit" {
  bucket = aws_s3_bucket.raw_audit.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "raw_audit" {
  bucket = aws_s3_bucket.raw_audit.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable server-side encryption (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "raw_audit" {
  bucket = aws_s3_bucket.raw_audit.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy: Transition to Glacier after 90 days, expire after 7 years
resource "aws_s3_bucket_lifecycle_configuration" "raw_audit" {
  bucket = aws_s3_bucket.raw_audit.id

  rule {
    id     = "TransitionToGlacierAndDelete"
    status = "Enabled"

    filter {}

    transition {
      days          = var.s3_glacier_transition_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.s3_expiration_days
    }
  }
}
