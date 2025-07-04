from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.db.database import get_session
from services.db.models import SpecialSituation  # type: ignore[attr-defined]

router = APIRouter(prefix="/specials", tags=["Special Situations"])


class SpecialItem(BaseModel):
    id: int
    symbol: str
    filing_type: str
    filed_at: datetime | None = None
    url: str | None = None


@router.get("/latest", response_model=List[SpecialItem])
def latest_specials(limit: int = 20, db: Session = Depends(get_session)):
    stmt = (
        select(SpecialSituation)
        .order_by(SpecialSituation.filed_at.desc().nullslast(), SpecialSituation.created_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    return rows