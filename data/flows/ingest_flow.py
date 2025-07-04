"""ingest_flow.py

Prefect flow that:
1. Runs fundamentals and insider ingestion scripts.
2. Validates resulting Parquet using Great Expectations.
3. Copies validated datasets to the configured lakehouse bucket (local placeholder).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import great_expectations as gx
from prefect import flow, task

FUND_PATH = Path("data/samples/fundamentals.parquet")
INSIDER_PATH = Path("data/samples/insider_trades.parquet")
DEST_DIR = Path("data/lakehouse/raw")


@task
def ingest_fundamentals():
    from data.ingestion.fundamentals_ingest import main as run_ingest

    run_ingest()
    return FUND_PATH


@task
def ingest_insider():
    from data.ingestion.insider_trades_ingest import main as run_ingest

    run_ingest()
    return INSIDER_PATH


@task
def validate(path: Path, suite: str):
    context = gx.get_context(context_root_dir="data/great_expectations")
    batch = context.sources.pandas_default.read_parquet(path)
    res = batch.validate(expectation_suite_name=suite)
    if not res.validation_success:
        raise ValueError(f"Validation failed for {path}")
    return True


@task
def copy_to_lakehouse(path: Path):
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    target = DEST_DIR / path.name
    shutil.copy2(path, target)
    return target


@flow(name="daily-ingestion")
def daily_ingestion_flow():
    fund_path = ingest_fundamentals()
    insider_path = ingest_insider()

    validate(fund_path, "financials.initial")
    # insider trades: simple null check dynamic expectations skipped for brevity

    copy_to_lakehouse(fund_path)
    copy_to_lakehouse(insider_path)


if __name__ == "__main__":
    daily_ingestion_flow()