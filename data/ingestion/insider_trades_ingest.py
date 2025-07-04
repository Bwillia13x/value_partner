"""insider_trades_ingest.py

Alternative data ingestion script for insider transaction filings.
This Phase-3 demo generates synthetic Form-4 style records and stores them as Parquet.
Replace with real data-provider API in production (e.g., Quiver, InsiderScore).
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from random import choice, randint, uniform

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
POSITIONS = ["CEO", "CFO", "Director", "VP"]
TRAN_TYPES = ["Purchase", "Sale"]


def synthetic_insider_trades(n: int = 100) -> pd.DataFrame:
    """Generate *n* fake insider trade records."""
    base_date = datetime.today()
    rows = []
    for _ in range(n):
        date = base_date - timedelta(days=randint(1, 365))
        rows.append(
            {
                "date": date.date(),
                "ticker": choice(TICKERS),
                "insider_position": choice(POSITIONS),
                "shares": randint(500, 50000),
                "price": round(uniform(20, 350), 2),
                "transaction_type": choice(TRAN_TYPES),
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate or ingest insider trade data.")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--output", default="data/samples/insider_trades.parquet", help="Parquet output path"
    )
    args = parser.parse_args()

    df = synthetic_insider_trades(args.count)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    logging.info("Wrote %d records to %s", len(df), out_path)


if __name__ == "__main__":
    main()