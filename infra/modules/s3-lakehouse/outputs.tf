output "bucket_name" {
  description = "S3 bucket backing the data lakehouse"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the lakehouse S3 bucket"
  value       = aws_s3_bucket.this.arn
}