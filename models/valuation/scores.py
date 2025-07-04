"""Quality / earnings-manipulation score calculations.

All formulas are streamlined versions of academic models, designed to run on
plain Python numerics (no pandas dependency).  Inputs should be pre-computed
ratios or totals as documented per function.
"""
from __future__ import annotations

import math
from typing import Dict, List

__all__ = [
    "piotroski_f_score",
    "beneish_m_score",
    "sloan_accruals_ratio",
    "altman_z_score",
    "cagr",
]


# ---------------------------------------------------------------------------
# 1. Piotroski F-Score (0–9)
# ---------------------------------------------------------------------------

def piotroski_f_score(cur: Dict[str, float], prev: Dict[str, float]) -> int:
    """Return Piotroski F-Score using current & previous year metrics.

    Parameters
    ----------
    cur, prev
        Dictionaries keyed by:
        roa – Return on Assets
        cfo – Cash flow from operations / Total Assets
        leverage – Long-term debt / Total Assets (lower is better)
        current_ratio – Current ratio (Current Assets / Current Liabilities)
        shares_out – Common shares outstanding
        gross_margin – Gross profit / Revenue
        asset_turnover – Revenue / Total Assets

    Example
    -------
    >>> cur = {"roa": 0.05, "cfo": 0.06, "leverage": 0.3, "current_ratio": 1.6,
    ...        "shares_out": 1_000_000, "gross_margin": 0.35, "asset_turnover": 1.1}
    >>> prev = {"roa": 0.02, "cfo": 0.04, "leverage": 0.35, "current_ratio": 1.4,
    ...        "shares_out": 1_050_000, "gross_margin": 0.32, "asset_turnover": 1.0}
    >>> piotroski_f_score(cur, prev)
    8
    """

    score = 0

    # Profitability
    score += 1 if cur["roa"] > 0 else 0
    score += 1 if cur["cfo"] > 0 else 0
    score += 1 if cur["roa"] > prev["roa"] else 0
    accrual = cur["cfo"] - cur["roa"]
    score += 1 if accrual > 0 else 0

    # Leverage / liquidity
    score += 1 if cur["leverage"] < prev["leverage"] else 0
    score += 1 if cur["current_ratio"] > prev["current_ratio"] else 0
    score += 1 if cur["shares_out"] <= prev["shares_out"] else 0

    # Operating efficiency
    score += 1 if cur["gross_margin"] > prev["gross_margin"] else 0
    score += 1 if cur["asset_turnover"] > prev["asset_turnover"] else 0

    return score


# ---------------------------------------------------------------------------
# 2. Beneish M-Score (1999 model) – earnings manipulation probability
# ---------------------------------------------------------------------------


def beneish_m_score(ratios: Dict[str, float]) -> float:
    """Compute Beneish M-Score given eight pre-computed ratios.

    Keys required in *ratios* dict:
        dsri – Days Sales Receivable Index
        gmi  – Gross Margin Index
        aqi  – Asset Quality Index
        sgi  – Sales Growth Index
        depi – Depreciation Index
        sgai – SG&A Expenses Index
        lvgi – Leverage Index
        tata – Total Accruals to Total Assets

    A value > ‑1.78 suggests possible manipulation.
    """

    dsri = ratios["dsri"]
    gmi = ratios["gmi"]
    aqi = ratios["aqi"]
    sgi = ratios["sgi"]
    depi = ratios["depi"]
    sgai = ratios["sgai"]
    lvgi = ratios["lvgi"]
    tata = ratios["tata"]

    m_score = (
        -4.84
        + 0.92 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    return m_score


# ---------------------------------------------------------------------------
# 3. Sloan Accruals (quality of earnings)
# ---------------------------------------------------------------------------

def sloan_accruals_ratio(net_income: float, cash_flow_ops: float, total_assets: float) -> float:
    """Return Sloan accruals ratio (NI − CFO) / Total Assets.

    Higher absolute values (> ~0.10) may indicate earnings manipulation.
    """
    if total_assets == 0:
        raise ValueError("total_assets cannot be zero")
    return (net_income - cash_flow_ops) / total_assets


# ---------------------------------------------------------------------------
# 4. Altman Z-Score (public manufacturing firm variant)
# ---------------------------------------------------------------------------

def altman_z_score(
    working_capital: float,
    retained_earnings: float,
    ebit: float,
    market_equity: float,
    total_liabilities: float,
    total_assets: float,
    sales: float,
) -> float:
    """Compute Altman Z-Score for publicly traded manufacturing companies.

    Z = 1.2 * (WC/TA) + 1.4 * (RE/TA) + 3.3 * (EBIT/TA) + 0.6 * (ME/TL) + 1.0 * (Sales/TA)
    """
    if total_assets == 0 or total_liabilities == 0:
        raise ValueError("total_assets and total_liabilities cannot be zero")

    z = (
        1.2 * (working_capital / total_assets)
        + 1.4 * (retained_earnings / total_assets)
        + 3.3 * (ebit / total_assets)
        + 0.6 * (market_equity / total_liabilities)
        + 1.0 * (sales / total_assets)
    )
    return z


# ---------------------------------------------------------------------------
# 5. CAGR utilities
# ---------------------------------------------------------------------------

def cagr(values: List[float]) -> float:
    """Compound Annual Growth Rate for *values* covering evenly spaced years.

    Parameters
    ----------
    values : list
        Sequence ordered [oldest, …, latest] (length >= 2).
    """
    if len(values) < 2:
        raise ValueError("Need at least two values to compute CAGR")
    begin, end = values[0], values[-1]
    years = len(values) - 1
    if begin <= 0:
        raise ValueError("Starting value must be positive for CAGR")
    return (end / begin) ** (1 / years) - 1