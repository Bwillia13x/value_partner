"""momentum.py

Functions to compute momentum overlays such as 12-1 month momentum and short-term reversal.

Input is a price DataFrame indexed by date & ticker (or with explicit columns) and monthly frequency.
"""
from __future__ import annotations

import pandas as pd


def trailing_return(df: pd.DataFrame, lookback: int = 12, skip: int = 1, price_col: str = "price") -> pd.Series:
    """Compute trailing total return over *lookback* months, skipping most recent *skip* months.

    For classical 12-1 momentum, set lookback=12, skip=1.
    """
    # assume df is sorted by date
    shifted = df.groupby("ticker")[price_col].shift(skip)
    lagged = df.groupby("ticker")[price_col].shift(lookback + skip)
    return (shifted / lagged - 1).rename("momentum_{lb}_{sk}".format(lb=lookback, sk=skip))


def compute_momentum(df_prices: pd.DataFrame, lookback: int = 12, skip: int = 1, price_col: str = "price") -> pd.DataFrame:
    """Return DataFrame with additional momentum column appended to *df_prices* (same shape)."""
    m = trailing_return(df_prices, lookback, skip, price_col)
    out = df_prices.copy()
    out[f"mom_{lookback}_{skip}"] = m
    return out