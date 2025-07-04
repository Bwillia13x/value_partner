from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.db.database import get_session
from sqlalchemy.orm import Session

from services.app.valuation_service import compute_valuation

router = APIRouter(prefix="/valuation", tags=["Valuation"])


class QualityScores(BaseModel):
    piotroski: int | None = Field(None, description="Piotroski F-Score (0-9)")
    beneish: float | None = Field(None, description="Beneish M-Score")
    # room for Sloan, Altman later


class ValuationResponse(BaseModel):
    symbol: str
    base: float | None = None
    bear: float | None = None
    bull: float | None = None
    undervaluation: float | None = Field(None, description="Positive => undervalued")
    quality: QualityScores | None = None
    price: float | None = None


@router.get("/{symbol}", response_model=ValuationResponse)
def get_valuation(symbol: str, db: Session = Depends(get_session)):
    """Return intrinsic value estimates and quality scores for *symbol*."""

    # Currently compute_valuation ignores db but in next phase it will pull data.
    try:
        result = compute_valuation(symbol)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result