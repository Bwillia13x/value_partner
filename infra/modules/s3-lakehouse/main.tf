resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  force_destroy = false

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = var.kms_key_arn
      }
    }
  }

  tags = {
    purpose = "data-lakehouse"
  }
}

resource "aws_s3_bucket_policy" "require_tls" {
  bucket = aws_s3_bucket.this.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "DenyInsecureTransport",
        Effect    = "Deny",
        Principal = "*",
        Action    = "s3:*",
        Resource = [
          aws_s3_bucket.this.arn,
          "${aws_s3_bucket.this.arn}/*"
        ],
        Condition = {
          Bool = {"aws:SecureTransport": "false"}
        }
      },
      {
        Sid       = "DenyUnEncryptedObjectUploads",
        Effect    = "Deny",
        Principal = "*",
        Action    = "s3:PutObject",
        Resource = "${aws_s3_bucket.this.arn}/*",
        Condition = {
          StringNotEquals = {"s3:x-amz-server-side-encryption": "aws:kms"}
        }
      }
    ]
  })
}