"""transaction_cost.py

Approximate transaction-cost models for equity trading.
Includes square-root market impact (Kyle/Torre) and Almgren-Chriss temporary cost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sqrt_impact(volume: pd.Series, k: float = 0.1, daily_vol: float = 0.02) -> pd.Series:
    """Square-root impact model: cost = k * daily_vol * sqrt(|v|/ADV).
    Here `volume` is trade size as % of ADV.
    """
    return k * daily_vol * np.sqrt(np.abs(volume)) * np.sign(volume)


def almgren_chriss_temp(cost_per_share: float, eta: float, shares: pd.Series, time_horizon: float) -> pd.Series:
    """Almgren-Chriss temporary cost: eta * shares/time_horizon.
    `cost_per_share` acts as permanent cost baseline.
    Returns cost in dollars.
    """
    return cost_per_share * shares + eta * shares / time_horizon