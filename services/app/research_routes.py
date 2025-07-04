from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from services.db.database import get_session
from services.db.models import ResearchNote  # type: ignore[attr-defined]
from services.app.valuation_service import compute_valuation

router = APIRouter(prefix="/research", tags=["Research Notebook"])


class NoteIn(BaseModel):
    symbol: str
    content: str


class NoteOut(BaseModel):
    id: int
    symbol: str
    version: int
    content: str
    snapshot: dict | None = None
    created_at: datetime


@router.post("/add", response_model=NoteOut)
def add_note(note: NoteIn, db: Session = Depends(get_session)):
    """Add a new versioned research note."""
    # determine next version number
    next_ver = (
        db.execute(
            select(func.coalesce(func.max(ResearchNote.version), 0)).where(ResearchNote.symbol == note.symbol.upper())
        ).scalar_one()
    ) + 1

    snapshot = compute_valuation(note.symbol)  # include current valuation snapshot
    rn = ResearchNote(
        symbol=note.symbol.upper(),
        version=next_ver,
        content=note.content,
        snapshot=snapshot,
        created_at=datetime.utcnow(),
    )
    db.add(rn)
    db.commit()
    db.refresh(rn)
    return rn


@router.get("/{symbol}", response_model=List[NoteOut])
def list_notes(symbol: str, db: Session = Depends(get_session)):
    """List all notes for a symbol (newest first)."""
    rows = db.execute(
        select(ResearchNote).where(ResearchNote.symbol == symbol.upper()).order_by(ResearchNote.version.desc())
    ).scalars().all()
    return rows


@router.get("/{symbol}/{version}", response_model=NoteOut)
def get_note(symbol: str, version: int, db: Session = Depends(get_session)):
    note = db.execute(
        select(ResearchNote).where(
            (ResearchNote.symbol == symbol.upper()) & (ResearchNote.version == version)
        )
    ).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note