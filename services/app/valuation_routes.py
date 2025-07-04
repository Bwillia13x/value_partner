from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/valuation", tags=["Valuation"])


class ValuationResponse(BaseModel):
    symbol: str
    base: float | None = None
    bear: float | None = None
    bull: float | None = None
    undervaluation: float | None = None


@router.get("/{symbol}", response_model=ValuationResponse)
def get_valuation(symbol: str):
    # TODO: connect to valuation engine / database.
    dummy = ValuationResponse(
        symbol=symbol.upper(),
        base=100.0,
        bear=80.0,
        bull=130.0,
        undervaluation=0.25,
    )
    return dummy