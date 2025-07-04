"""fundamentals_ingest.py

Phase-1 ingestion script that pulls basic fundamental metrics via yfinance (free, for demo)
and writes a Parquet file suitable for Great Expectations validation and factor calculation.

This is **not** production-grade; in later phases replace with licensed point-in-time provider (e.g., Compustat).
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


COLUMNS_MAP = {
    "trailingPE": "pe_ratio",
    "priceToBook": "pb_ratio",
    "enterpriseToEbitda": "ev_ebitda",
    "returnOnEquity": "roe",
    "debtToEquity": "de_ratio",
}


def fetch_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """Fetch selected fundamentals for given ticker list."""
    data = []
    for ticker in tickers:
        logging.info("Fetching fundamentals for %s", ticker)
        info = yf.Ticker(ticker).info
        row = {"ticker": ticker}
        for yf_key, col in COLUMNS_MAP.items():
            row[col] = info.get(yf_key)
        data.append(row)
    df = pd.DataFrame(data)
    return df


def main():
    parser = argparse.ArgumentParser(description="Ingest fundamentals via yfinance and write Parquet file.")
    parser.add_argument("--tickers", nargs="*", default=["AAPL", "MSFT", "GOOGL"], help="Ticker symbols")
    parser.add_argument("--output", default="data/samples/fundamentals.parquet", help="Output Parquet path")
    args = parser.parse_args()

    df = fetch_fundamentals(args.tickers)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logging.info("Wrote %d rows to %s", len(df), output_path)


if __name__ == "__main__":
    main()