output "bucket_name" {
  description = "S3 bucket backing the data lakehouse"
  value       = aws_s3_bucket.this.id
}