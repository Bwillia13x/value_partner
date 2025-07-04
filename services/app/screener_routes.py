from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.db.database import get_session
from services.db.models import KeyMetric, IntrinsicValuation  # type: ignore[attr-defined]

router = APIRouter(prefix="/screeners", tags=["Screeners"])


class ScreenerItem(BaseModel):
    symbol: str
    roic: float | None = None
    fcf_years: int | None = None
    debt_ebitda: float | None = None
    price: float | None = None
    intrinsic_value: float | None = None
    magic_formula_score: float | None = None


# ---------------------------------------------------------------------------
# Buffettology Screener
# ---------------------------------------------------------------------------


@router.get("/buffettology", response_model=List[ScreenerItem])
def buffettology_screener(limit: int = 50, db: Session = Depends(get_session)):
    """Return companies passing Buffettology filters."""

    # Pull all metrics (could filter by timeframe in production)
    rows = db.execute(select(KeyMetric)).scalars().all()

    # Organize metrics by symbol
    sym_metrics: dict[str, dict[str, list[float]]] = {}
    for m in rows:
        sym_metrics.setdefault(m.symbol, {}).setdefault(m.metric_name, []).append(m.value)

    # Fetch intrinsic values
    valuations = db.execute(select(IntrinsicValuation)).scalars().all()
    intrinsic_map = {v.symbol: v.base_value for v in valuations if v.base_value is not None}

    passed: List[ScreenerItem] = []
    for sym, m in sym_metrics.items():
        roic = (m.get("ROIC") or [None])[0]
        debt_ebitda = (m.get("DebtToEBITDA") or [None])[0]
        price = (m.get("price") or [None])[0]
        intrinsic_value = intrinsic_map.get(sym)

        # FCF positive years
        fcf_values = m.get("FCF", [])
        fcf_years = sum(1 for v in fcf_values if v and v > 0)

        if (
            roic is not None and roic >= 0.15 and
            fcf_years >= 10 and
            (debt_ebitda is None or debt_ebitda < 2) and
            price is not None and intrinsic_value is not None and price < 0.8 * intrinsic_value
        ):
            passed.append(
                ScreenerItem(
                    symbol=sym,
                    roic=roic,
                    fcf_years=fcf_years,
                    debt_ebitda=debt_ebitda,
                    price=price,
                    intrinsic_value=intrinsic_value,
                )
            )

    passed.sort(key=lambda x: x.roic or 0, reverse=True)
    return passed[:limit]


# ---------------------------------------------------------------------------
# Magic Formula ranking
# ---------------------------------------------------------------------------


@router.get("/magic-formula", response_model=List[ScreenerItem])
def magic_formula(limit: int = 50, db: Session = Depends(get_session)):
    """Return Magic Formula ranking based on ROIC and Earnings Yield."""

    rows = db.execute(select(KeyMetric)).scalars().all()

    sym_data: dict[str, dict[str, float]] = {}
    for k in rows:
        sym_data.setdefault(k.symbol, {})[k.metric_name] = k.value or 0.0

    # Compute rankings lists
    roic_ranking = sorted(
        ((sym, data.get("ROIC", 0.0)) for sym, data in sym_data.items()), key=lambda x: x[1], reverse=True
    )
    ey_ranking = sorted(
        ((sym, data.get("EarningsYield", 0.0)) for sym, data in sym_data.items()), key=lambda x: x[1], reverse=True
    )

    roic_rank = {sym: idx + 1 for idx, (sym, _) in enumerate(roic_ranking)}
    ey_rank = {sym: idx + 1 for idx, (sym, _) in enumerate(ey_ranking)}

    combined = []
    for sym in sym_data.keys():
        score = roic_rank.get(sym, len(sym_data)) + ey_rank.get(sym, len(sym_data))
        combined.append((sym, score))

    combined.sort(key=lambda x: x[1])  # lower score better

    result: List[ScreenerItem] = []
    for sym, score in combined[:limit]:
        m = sym_data[sym]
        result.append(
            ScreenerItem(
                symbol=sym,
                roic=m.get("ROIC"),
                magic_formula_score=score,
            )
        )
    return result