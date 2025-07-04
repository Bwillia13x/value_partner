# Infrastructure as Code (IaC)

This directory contains all Terraform configurations required to provision and manage the cloud resources that underpin the institutional-grade value-investing platform.

Current scope (Phase 1):
1. **Data-lakehouse foundation** – S3 bucket with versioning & encryption, ready for Delta Lake/Iceberg tables.
2. Remote state backend (S3 + DynamoDB) placeholders.
3. Modular structure for future Glue, Athena, Redshift, EMR, and security resources.

> Every change must go through pull-request review and pass the CI pipeline (`terraform fmt`, `terraform validate`, and plan review) before being merged.

- **KMS key** – customer-managed key with rotation enabled (module `kms_lakehouse`).