"""compustat_ingest.py

Illustrative integration with S&P Global/Compustat Datahub API.
Reads API key from env COMPUSTAT_API_KEY.
Sends request to fetch fundamentals for tickers and writes Parquet.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.compustat.com/fundamentals"  # placeholder


def fetch_compustat(tickers: list[str], api_key: str) -> pd.DataFrame:
    all_rows = []
    headers = {"Authorization": f"Bearer {api_key}"}
    for ticker in tickers:
        resp = requests.get(f"{BASE_URL}/{ticker}", headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"Failed to fetch {ticker}: {resp.text}", file=sys.stderr)
            continue
        data = resp.json()
        all_rows.append(data)
    return pd.DataFrame(all_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=["AAPL", "MSFT", "GOOGL"])
    parser.add_argument("--output", default="data/samples/compustat_fundamentals.parquet")
    args = parser.parse_args()

    api_key = os.getenv("COMPUSTAT_API_KEY")
    if not api_key:
        raise RuntimeError("COMPUSTAT_API_KEY not set")

    df = fetch_compustat(args.tickers, api_key)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"Saved Compustat fundamentals to {out_path}")


if __name__ == "__main__":
    main()