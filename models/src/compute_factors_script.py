"""compute_factors_script.py

CLI utility to compute value factors from a fundamentals Parquet file.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from models.src.factors import compute_factors  # type: ignore


def main():
    parser = argparse.ArgumentParser(description="Compute value factors from fundamentals dataset.")
    parser.add_argument("--input", default="data/samples/fundamentals.parquet", help="Input fundamentals Parquet")
    parser.add_argument("--output", default="data/samples/factors.parquet", help="Output Parquet with factors")
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    out_df = compute_factors(df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(output_path, index=False)
    print(f"Wrote factors to {output_path} – {len(out_df)} rows")


if __name__ == "__main__":
    main()