"""compustat_ingest.py

Illustrative integration with S&P Global/Compustat Datahub API.
Reads API key from env COMPUSTAT_API_KEY.
Sends request to fetch fundamentals for tickers and writes Parquet.
"""
from __future__ import annotations

import argparse
from pathlib import Path


from data.providers.compustat_provider import CompustatProvider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=["AAPL", "MSFT", "GOOGL"])
    parser.add_argument("--output", default="data/samples/compustat_fundamentals.parquet")
    args = parser.parse_args()

    provider = CompustatProvider()
    df = provider.fetch_fundamentals(args.tickers)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"Saved Compustat fundamentals to {out_path}")


if __name__ == "__main__":
    main()