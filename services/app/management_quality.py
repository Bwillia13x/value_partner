"""Management quality scoring utilities.

Weights insider ownership, buy/sell behaviour, compensation alignment, tenure
stability and capital-allocation track record to derive a 0-1 quality score.

Inputs are kept deliberately simple numbers so upstream ETL tasks can map raw
provider payloads into these fields.
"""
from __future__ import annotations

from typing import Dict

from services.db.database import SessionLocal
from services.db.models import QualitativeSignal  # type: ignore[attr-defined]

__all__ = ["compute_management_quality", "store_management_quality"]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:  # noqa: WPS110
    return max(lo, min(value, hi))


def compute_management_quality(metrics: Dict[str, float]) -> float:
    """Return composite management quality score ∈ [0,1].

    Expected keys in *metrics* dict:
        insider_ownership_pct  – Fraction of shares held by insiders (0-1).
        buy_sell_ratio         – Insider buy $ / (buy $ + sell $) (0-1).
        comp_perf_ratio        – Exec comp / Net income (lower is better, typical 0-0.1).
        avg_tenure_years       – Average C-suite tenure.
        capital_allocation     – 0-1 score summarising buybacks, capex discipline, etc.
    """

    # 1. Insider ownership – ideal around 20-25%
    insider = _clamp(metrics.get("insider_ownership_pct", 0) / 0.25)

    # 2. Buy vs sell ratio – already 0-1
    buy_sell = _clamp(metrics.get("buy_sell_ratio", 0))

    # 3. Compensation alignment – lower better. Assume 0 => perfect; >=0.1 => poor
    comp_ratio = metrics.get("comp_perf_ratio", 0.1)
    comp_score = _clamp(1 - comp_ratio / 0.1)

    # 4. Tenure – bell curve centred ~8 yrs (3-15 good)
    tenure = metrics.get("avg_tenure_years", 0)
    tenure_score = _clamp(1 - abs(tenure - 8) / 8)

    # 5. Capital allocation – passed directly (0-1)
    cap_alloc = _clamp(metrics.get("capital_allocation", 0))

    # Equal weights
    composite = (insider + buy_sell + comp_score + tenure_score + cap_alloc) / 5
    return composite


def store_management_quality(symbol: str, metrics: Dict[str, float]) -> float:
    """Compute and persist management quality signal row. Returns score."""
    score = compute_management_quality(metrics)

    session = SessionLocal()
    try:
        signal = QualitativeSignal(
            symbol=symbol.upper(),
            signal_type="management_quality",
            score=score,
            data=metrics,
        )
        session.add(signal)
        session.commit()
    finally:
        session.close()
    return score