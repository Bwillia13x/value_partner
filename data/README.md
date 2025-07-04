# Data Layer

This directory will hold data ingestion pipelines, transformation logic, and data-quality tests.

Proposed sub-folders:

* `ingestion/` – scripts or DAG tasks that pull raw data (e.g., Compustat, Refinitiv, alternative data) into the `raw` zone.
* `transform/` – dbt models or Spark notebooks that convert raw data to curated and feature layers.
* `expectations/` – Great Expectations suites for automated data-quality validation.
* `samples/` – very small CSV/Parquet files for unit-testing purposes only (do **not** commit licensed datasets).

> All ingestion jobs will be orchestrated via Airflow/Prefect in later phases and land data in the lakehouse bucket defined by Terraform.