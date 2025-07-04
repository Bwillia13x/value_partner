"""gips.py

Functions to compute GIPS-compliant time-weighted returns (TWR) and statistics.
Assumes period (e.g., monthly) returns provided.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def link_time_weighted(returns: pd.Series) -> pd.Series:
    """Geometrically link period returns to cumulative return series."""
    cumulative = (1 + returns).cumprod() - 1
    return cumulative


def annualized_return(total_return: float, n_periods: int, periods_per_year: int = 12) -> float:
    """Convert total return over n_periods to annualized."""
    return (1 + total_return) ** (periods_per_year / n_periods) - 1


def gips_metrics(returns: pd.Series, rf_rate: float = 0.0, periods_per_year: int = 12) -> dict[str, float]:
    """Compute key GIPS metrics from period returns series."""
    cumulative = link_time_weighted(returns).iloc[-1]
    ann_ret = annualized_return(cumulative, len(returns), periods_per_year)
    ann_vol = returns.std(ddof=0) * np.sqrt(periods_per_year)
    sharpe = (ann_ret - rf_rate) / ann_vol if ann_vol else np.nan
    max_dd = (link_time_weighted(returns).cummax() - link_time_weighted(returns)).max()
    return {
        "total_return": cumulative,
        "annualized_return": ann_ret,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
    }