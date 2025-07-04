"""Discounted-cash-flow valuation helpers.

This module purposefully keeps the math lightweight and dependency-free while
 providing enough flexibility for common valuation workflows.  The algorithms
 are *simplified* compared to full-fledged analyst models, but the inputs map
 directly to the parameters typically surfaced in UI sliders / REST payloads
 (growth rates, discount / WACC, terminal growth).

Key helpers
----------
discounted_cash_flow       – Basic single-vector DCF (with terminal value).
two_stage_dcf              – Explicit forecast period then perpetual growth.
three_stage_dcf            – High-growth → transition → terminal.
reverse_dcf                – Solve for the constant growth rate that
                              reconciles price ↔ intrinsic value.
"""

from __future__ import annotations

from typing import Iterable, List


# ---------------------------------------------------------------------------
# 1. Basic utility
# ---------------------------------------------------------------------------


def _present_value(cash_flow: float, discount_rate: float, period: int) -> float:
    """Return present value of *cash_flow* received at *period* (1-indexed)."""
    return cash_flow / ((1 + discount_rate) ** period)


# ---------------------------------------------------------------------------
# 2. Simplified vector-based DCF (kept for backwards compatibility)
# ---------------------------------------------------------------------------


def discounted_cash_flow(
    cash_flows: Iterable[float],
    discount_rate: float = 0.1,
    terminal_growth: float = 0.03,
) -> float:
    """DCF given explicit yearly *cash_flows* followed by perpetual growth.

    Parameters
    ----------
    cash_flows
        An iterable of projected free-cash-flow amounts (already nominal).
    discount_rate
        Discount / WACC expressed as decimal (e.g. 0.08 => 8 %).
    terminal_growth
        Constant perpetual growth applied after the final explicit year.
    """

    cash_flows = list(cash_flows)

    if not cash_flows:
        raise ValueError("cash_flows cannot be empty")

    # PV of explicit forecast period
    pv_operating = sum(_present_value(cf, discount_rate, i) for i, cf in enumerate(cash_flows, 1))

    # Gordon-growth terminal value based on the last explicit CF
    tv = cash_flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = _present_value(tv, discount_rate, len(cash_flows))

    return pv_operating + pv_terminal


# ---------------------------------------------------------------------------
# 3. Two- and three-stage helpers
# ---------------------------------------------------------------------------


def two_stage_dcf(
    starting_fcf: float,
    growth_rate_stage1: float,
    years_stage1: int,
    growth_rate_stage2: float,
    discount_rate: float,
) -> float:
    """Two-stage DCF where each stage uses constant *growth_rate*.

    1. Stage-1: high/medium growth at *growth_rate_stage1* for *years_stage1*.
    2. Stage-2: perpetual growth at *growth_rate_stage2* with Gordon formula.
    """

    # Build explicit CF vector for stage-1 years
    cash_flows: List[float] = []
    fcf = starting_fcf
    for _ in range(years_stage1):
        fcf *= 1 + growth_rate_stage1
        cash_flows.append(fcf)

    intrinsic = discounted_cash_flow(
        cash_flows,
        discount_rate=discount_rate,
        terminal_growth=growth_rate_stage2,
    )

    return intrinsic


def three_stage_dcf(
    starting_fcf: float,
    growth_rate_stage1: float,
    years_stage1: int,
    growth_rate_stage2: float,
    years_stage2: int,
    terminal_growth_rate: float,
    discount_rate: float,
) -> float:
    """Three-stage DCF: high growth → fading growth → terminal.

    Stage-1: growth_rate_stage1 for years_stage1.
    Stage-2: growth_rate_stage2 for years_stage2.
    Stage-3: perpetual *terminal_growth_rate*.
    """

    cash_flows: List[float] = []
    fcf = starting_fcf

    # Stage-1 CFs
    for _ in range(years_stage1):
        fcf *= 1 + growth_rate_stage1
        cash_flows.append(fcf)

    # Stage-2 CFs
    for _ in range(years_stage2):
        fcf *= 1 + growth_rate_stage2
        cash_flows.append(fcf)

    intrinsic = discounted_cash_flow(
        cash_flows,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth_rate,
    )

    return intrinsic


# ---------------------------------------------------------------------------
# 4. Reverse DCF – solve for implied growth
# ---------------------------------------------------------------------------


def reverse_dcf(
    market_value: float,
    starting_fcf: float,
    years: int,
    discount_rate: float,
    terminal_growth: float,
    tol: float = 1e-4,
    max_iter: int = 100,
) -> float:
    """Return the constant annual growth rate that equates DCF to *market_value*.

    Simple binary-search root-finding between ‑100 % and +100 % growth.
    """

    low, high = -0.99, 1.0  # bounds for growth rate
    for _ in range(max_iter):
        mid = (low + high) / 2
        # Build CF vector given *mid* growth
        cf_vec = [starting_fcf * ((1 + mid) ** t) for t in range(1, years + 1)]
        intrinsic = discounted_cash_flow(cf_vec, discount_rate, terminal_growth)
        if abs(intrinsic - market_value) < tol:
            return mid
        if intrinsic > market_value:
            high = mid
        else:
            low = mid
    return mid  # best effort