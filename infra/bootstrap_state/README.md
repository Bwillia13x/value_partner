# Terraform Remote State Bootstrap

This sub-directory contains a one-time Terraform configuration that provisions the S3 bucket and DynamoDB lock table used for the global remote state backend.  Run **before** any other Terraform in this repo.

```bash
cd infra/bootstrap_state
terraform init
terraform apply -auto-approve
```

Outputs include:
* `state_bucket_name` – S3 bucket for tfstate files (versioning + encryption)
* `dynamodb_table_name` – table used for state locking

Once created, update `infra/main.tf` backend block—or run `terraform init -reconfigure`—so all modules share the centralized state.