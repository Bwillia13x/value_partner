from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select

from services.app.tasks.celery_app import app
from services.app.data_providers.sec_edgar import SecEdgarProvider
from services.db.database import SessionLocal
from services.db.models import SpecialSituation  # type: ignore[attr-defined]

FORMS = ["10-12B", "10-12G", "S-4"]


@app.task(name="services.app.tasks.special_situations.scan")
def scan_special_situations(symbols: List[str] | None = None, limit: int = 5) -> str:
    """Scan SEC EDGAR for recent spinoff / merger filings and store new events."""
    provider = SecEdgarProvider()

    # basic symbol list fallback
    if symbols is None:
        symbols = ["AAPL", "MSFT"]

    session = SessionLocal()
    new_events = 0
    try:
        for sym in symbols:
            for form in FORMS:
                filings = provider.fetch(sym, form=form, limit=limit)
                for filing in filings.get("filings", []):
                    url = filing.get("linkToFilingDetails")
                    filed_at_str = filing.get("filedAt")
                    filed_at = (
                        datetime.fromisoformat(filed_at_str.replace("Z", "+00:00"))
                        if filed_at_str
                        else None
                    )

                    # Dedup by URL
                    exists = session.execute(
                        select(SpecialSituation).where(SpecialSituation.url == url)
                    ).scalar_one_or_none()
                    if exists or not url:
                        continue

                    event = SpecialSituation(
                        symbol=sym.upper(),
                        filing_type=form,
                        filed_at=filed_at,
                        url=url,
                        data=filing,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(event)
                    new_events += 1
        session.commit()
    finally:
        session.close()

    return f"Inserted {new_events} new special-situation events"