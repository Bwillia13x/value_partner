variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket that will hold the data lakehouse tables"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for bucket encryption"
}