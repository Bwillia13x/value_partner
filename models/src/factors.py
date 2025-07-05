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

    # --- Basic Value Factors ---
    # Note: These are common factors. A production system would include a much wider array,
    # potentially including: Price/Sales, Price/Cash Flow, FCF Yield, Dividend Yield, etc.
    # The composite scores below are also for demonstration and can be significantly enhanced.

    # Earnings yield is inverse of P/E. Handle potential zero P/E.
    # P/E can be negative if earnings are negative; earnings_yield will also be negative.
    # If P/E is zero (e.g. no earnings, or data issue), yield could be infinite or error.
    # We'll replace inf with NaN, which won't contribute to mean scores.
    out["earnings_yield"] = np.where(out["pe_ratio"] == 0, np.nan, 1 / out["pe_ratio"])


    # Book-to-market is inverse of Price-to-Book. Handle potential zero P/B.
    out["book_to_market"] = np.where(out["pb_ratio"] == 0, np.nan, 1 / out["pb_ratio"])

    # EV/EBITDA inverted to represent cheaper values higher. Handle potential zero EV/EBITDA.
    out["ev_ebitda_inverse"] = np.where(out["ev_ebitda"] == 0, np.nan, 1 / out["ev_ebitda"])

    # Composite value score: simple z-score average for demo.
    # Future enhancements: rank-based scores, industry-neutralization, outlier handling.
    numeric_cols = ["earnings_yield", "book_to_market", "ev_ebitda_inverse"]
    z_scores = (out[numeric_cols] - out[numeric_cols].mean()) / out[numeric_cols].std(ddof=0)
    out["value_score"] = z_scores.mean(axis=1)

    # Quality score: combination of high ROE and low leverage (debt-to-equity)
    q_z = pd.DataFrame(
        {
            "roe": (out["roe"] - out["roe"].mean()) / out["roe"].std(ddof=0),
            # Negative sign because lower debt is better
            "de_ratio": -(
                (out["de_ratio"] - out["de_ratio"].mean()) / out["de_ratio"].std(ddof=0)
            ),
        }
    )
    out["quality_score"] = q_z.mean(axis=1)

    # Combined value + quality (Magic Formula-style ranking)
    out["vq_score"] = (out["value_score"] + out["quality_score"]) / 2

    return out