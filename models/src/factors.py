"""factors.py

Utility functions to compute common value-investing factors from a pandas DataFrame containing
fundamental columns.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "roe",
    "de_ratio",
]


def compute_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with additional factor columns.

    Parameters
    ----------
    df : pd.DataFrame
        Must include ticker and required fundamental columns.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for factor calculation: {missing}")

    out = df.copy()

    # Earnings yield is inverse of P/E
    out["earnings_yield"] = 1 / out["pe_ratio"]

    # Book-to-market is inverse of Price-to-Book
    out["book_to_market"] = 1 / out["pb_ratio"]

    # EV/EBITDA inverted to represent cheaper values higher
    out["ev_ebitda_inverse"] = 1 / out["ev_ebitda"]

    # Composite value score: simple z-score average for demo
    numeric_cols = ["earnings_yield", "book_to_market", "ev_ebitda_inverse"]
    z_scores = (out[numeric_cols] - out[numeric_cols].mean()) / out[numeric_cols].std(ddof=0)
    out["value_score"] = z_scores.mean(axis=1)

    return out