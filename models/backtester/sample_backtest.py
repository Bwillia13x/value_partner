"""sample_backtest.py

Generate synthetic monthly returns for demonstration and run the Backtester.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from models.src.factors import compute_factors  # type: ignore
from models.backtester.backtester import Backtester
from models.analytics.gips import gips_metrics  # local import to avoid circular


def synthetic_data(n_months: int = 36):
    dates = pd.date_range("2020-01-31", periods=n_months, freq="M")
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]

    records = []
    rng = np.random.default_rng(0)
    for date in dates:
        for t in tickers:
            rec = {
                "date": date,
                "ticker": t,
                "pe_ratio": rng.uniform(5, 25),
                "pb_ratio": rng.uniform(0.5, 4),
                "ev_ebitda": rng.uniform(3, 15),
                "roe": rng.uniform(0.05, 0.25),
                "de_ratio": rng.uniform(0.1, 1.0),
            }
            records.append(rec)
    fundamentals = pd.DataFrame(records)
    factors = compute_factors(fundamentals)
    # Simulate next-month returns with some relationship to vq_score
    factors["return"] = rng.normal(loc=0.01 + 0.02 * factors["vq_score"], scale=0.05)
    return factors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=36)
    args = parser.parse_args()

    df = synthetic_data(args.months)
    bt = Backtester("vq_score", n_quantiles=5)
    cum_returns = bt.run(df)

    period_returns = df.groupby("date")["return"].mean()
    gips = gips_metrics(period_returns)

    stats = bt.performance_stats(cum_returns["Q1"])

    print("Cumulative returns quantiles:")
    print(cum_returns.tail())
    print("\nPerformance stats (Q1):")
    for k, v in stats.items():
        print(f"{k}: {v:.3%}")

    print("\nGIPS metrics (composite):")
    for k, v in gips.items():
        print(f"{k}: {v:.3%}")

    # Save output for compliance/reporting
    out_dir = Path("models/backtester/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    cum_returns.to_csv(out_dir / "cumulative_returns.csv")


if __name__ == "__main__":
    main()