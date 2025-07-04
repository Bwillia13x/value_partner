terraform {
  required_version = ">= 1.4.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.15"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for remote state bucket"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  type        = string
  default     = "value-investing-tfstate"
  description = "Name of S3 bucket to store Terraform remote state"
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm     = "aws:kms"
      }
    }
  }
  tags = {
    purpose = "terraform-state"
  }
}

resource "aws_dynamodb_table" "lock" {
  name         = "terraform-lock-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
  tags = {
    purpose = "terraform-state-lock"
  }
}

output "state_bucket_name" {
  value = aws_s3_bucket.state.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.lock.name
}