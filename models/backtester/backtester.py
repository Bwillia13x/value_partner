"""backtester.py

Lightweight, pandas-based backtester for cross-sectional factor strategies.
Assumptions:
* Input DataFrame contains `date`, `ticker`, `return`, and factor columns (e.g. `value_score`).
* Returns are already forward-looking for the holding horizon (e.g. next-month total return).

The class buckets securities into quantiles each rebalancing period and tracks equal-weighted
portfolio returns for the long top quantile (Q1) vs bottom (Q5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class Backtester:
    """Cross-sectional factor backtester."""

    def __init__(self, factor: str, n_quantiles: int = 5):
        self.factor = factor
        self.n_quantiles = n_quantiles

    def _assign_quantiles(self, df: pd.DataFrame) -> pd.Series:
        """Return quantile labels (1 = best) per date based on factor."""
        return (
            df.groupby("date")[self.factor]
            .transform(lambda x: pd.qcut(x.rank(method="first"), self.n_quantiles, labels=False) + 1)
        )

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run backtest and return cumulative returns per quantile."""
        required = {"date", "ticker", "return", self.factor}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Backtester missing required columns: {missing}")

        df = df.copy()
        df["q"] = self._assign_quantiles(df)

        # Compute average returns per quantile each period
        grouped = df.groupby(["date", "q"])["return"].mean().unstack(level="q")
        grouped = grouped.sort_index()  # date ascending

        # Cumulate
        cumulative = (1 + grouped).cumprod() - 1
        cumulative.columns = [f"Q{int(c)}" for c in cumulative.columns]
        return cumulative

    @staticmethod
    def performance_stats(cumret: pd.Series) -> dict[str, float]:
        """Compute simple performance metrics."""
        total_return = cumret.iloc[-1]
        period_returns = cumret.diff().fillna(cumret.iloc[0])  # first period same as first value
        ann_return = (1 + total_return) ** (12 / len(period_returns)) - 1  # monthly to annual
        ann_vol = period_returns.std() * np.sqrt(12)
        sharpe = ann_return / ann_vol if ann_vol else np.nan
        max_dd = (cumret.cummax() - cumret).max()
        return {
            "total_return": total_return,
            "annualized_return": ann_return,
            "annualized_vol": ann_vol,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
        }