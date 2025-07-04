terraform {
  required_version = ">= 1.4.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.15"
    }
  }

  # NOTE: replace the bucket/key once the remote state bucket is provisioned.
  backend "s3" {
    bucket = "state-bucket-placeholder"
    key    = "terraform/infra.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources into"
  default     = "us-east-1"
}

variable "lakehouse_bucket_name" {
  type        = string
  description = "Primary S3 bucket to act as the lakehouse storage layer"
  default     = "my-lakehouse-bucket"
}

variable "kms_key_alias" {
  type        = string
  description = "Alias for the KMS key used to encrypt lakehouse data"
  default     = "lakehouse-key"
}

# -------------------------------------------------------------------
#  Data-Lakehouse Foundation
# -------------------------------------------------------------------
module "kms_lakehouse" {
  source = "./modules/kms"
  alias  = var.kms_key_alias
}

module "s3_lakehouse" {
  source         = "./modules/s3-lakehouse"
  bucket_name    = var.lakehouse_bucket_name
  kms_key_arn    = module.kms_lakehouse.key_arn
}

module "iam_read_only" {
  source               = "./modules/iam-basic"
  lakehouse_bucket_arn = module.s3_lakehouse.bucket_arn
}

output "lakehouse_bucket" {
  description = "Name of the S3 bucket that backs the data lakehouse"
  value       = module.s3_lakehouse.bucket_name
}