"""convert_to_delta.py

Convert a Parquet dataset to Delta Lake format using delta-rs (deltalake package).
This is a local demonstration; in production run on EMR/Spark or Glue.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from deltalake.writer import write_deltalake


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input Parquet file")
    parser.add_argument("--output", required=True, help="Destination Delta table directory")
    args = parser.parse_args()

    df = pd.read_parquet(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_deltalake(output_dir, df, mode="overwrite")
    print(f"Converted {args.input} → {args.output} (Delta format)")


if __name__ == "__main__":
    main()