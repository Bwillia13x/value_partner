resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  force_destroy = false

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }

  tags = {
    purpose = "data-lakehouse"
  }
}