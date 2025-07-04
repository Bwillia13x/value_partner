"""Thin service layer that computes intrinsic value ranges and quality scores.

This implementation uses *placeholder* logic where real financial statement
parsing is not yet connected.  The purpose is to demonstrate end-to-end flow
so the /valuation API can already return meaningful numbers.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from models.valuation import (
    discounted_cash_flow,
    piotroski_f_score,
    beneish_m_score,
    margin_of_safety,
)
from services.app.data_providers import FMPProvider


def _get_market_price(symbol: str) -> Optional[float]:
    """Fetch latest market price via FMP *quote* endpoint if API key set."""
    try:
        provider = FMPProvider()
    except Exception:
        return None  # API key missing

    try:
        payload = provider.fetch(symbol, endpoint="quote")
        if isinstance(payload, list) and payload:
            return float(payload[0].get("price"))
    except Exception:
        pass
    return None


def compute_valuation(symbol: str) -> Dict[str, Any]:
    """Return valuation dict conforming to ValuationResponse schema downstream."""

    # ------------------------------
    # Simplified cash-flow inputs
    # ------------------------------
    # In a future phase these will come from DB; for now use synthetic growth.
    starting_fcf = 100.0  # assume $100m
    growth_rates = [0.05, 0.05, 0.04, 0.04, 0.03]
    cash_flows = [starting_fcf * (1 + g) ** i for i, g in enumerate(growth_rates, 1)]

    base_value = discounted_cash_flow(cash_flows, discount_rate=0.10, terminal_growth=0.03)
    bear_value = base_value * 0.8  # -20 % stress case
    bull_value = base_value * 1.3  # +30 % optimistic case

    # ------------------------------
    # Quality / manipulation score stubs
    # ------------------------------
    cur_metrics = {
        "roa": 0.06,
        "cfo": 0.07,
        "leverage": 0.25,
        "current_ratio": 1.8,
        "shares_out": 1_000_000,
        "gross_margin": 0.38,
        "asset_turnover": 1.1,
    }
    prev_metrics = {
        "roa": 0.04,
        "cfo": 0.05,
        "leverage": 0.28,
        "current_ratio": 1.6,
        "shares_out": 1_050_000,
        "gross_margin": 0.35,
        "asset_turnover": 1.0,
    }
    f_score = piotroski_f_score(cur_metrics, prev_metrics)

    m_score = beneish_m_score(
        {
            "dsri": 1.1,
            "gmi": 1.02,
            "aqi": 1.03,
            "sgi": 1.15,
            "depi": 1.01,
            "sgai": 1.04,
            "lvgi": 1.0,
            "tata": 0.05,
        }
    )

    # ------------------------------
    # Market price & undervaluation
    # ------------------------------
    price = _get_market_price(symbol)
    undervaluation = margin_of_safety(base_value, price) if price else None

    return {
        "symbol": symbol.upper(),
        "base": base_value,
        "bear": bear_value,
        "bull": bull_value,
        "undervaluation": undervaluation,
        "quality": {
            "piotroski": f_score,
            "beneish": m_score,
        },
        "price": price,
    }