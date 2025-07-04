output "role_arn" {
  value       = aws_iam_role.lakehouse_read.arn
  description = "ARN of the IAM role with lakehouse read-only access"
}