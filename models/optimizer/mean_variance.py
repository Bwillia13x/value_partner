"""mean_variance.py

Mean-variance optimizer using closed-form unconstrained solution or simple numerical solution with weight bounds.
Requirements: numpy, pandas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def mv_weights(returns: pd.DataFrame, risk_aversion: float = 1.0, weight_bounds: tuple[float, float] | None = None) -> pd.Series:
    """Compute mean-variance optimal weights.

    Parameters
    ----------
    returns : pd.DataFrame
        Asset return matrix (observations x assets).
    risk_aversion : float
        Lambda coefficient; higher = more risk-averse.
    weight_bounds : (lower, upper)
        If provided, weights are clipped to bounds then re-normalized.
    """
    mu = returns.mean().values  # expected returns
    cov = returns.cov().values
    inv = np.linalg.pinv(cov)
    raw = inv @ mu  # proportional to mean-variance optimization without constraints
    w = raw / raw.sum()

    if weight_bounds is not None:
        lower, upper = weight_bounds
        w = np.clip(w, lower, upper)
        w = w / w.sum()
    return pd.Series(w, index=returns.columns, name="weight")