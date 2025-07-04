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

# -------------------------------------------------------------------
#  Data-Lakehouse Foundation
# -------------------------------------------------------------------
module "s3_lakehouse" {
  source         = "./modules/s3-lakehouse"
  bucket_name    = var.lakehouse_bucket_name
}

output "lakehouse_bucket" {
  description = "Name of the S3 bucket that backs the data lakehouse"
  value       = module.s3_lakehouse.bucket_name
}