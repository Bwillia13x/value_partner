from typing import Any, Dict
from .base import DataProvider


class SecEdgarProvider(DataProvider):
    """Stub implementation for pulling filings from SEC EDGAR."""

    def fetch(self, symbol: str, form: str = "10-K") -> Dict[str, Any]:
        # TODO: Integrate with sec-api or similar package to pull filings.
        return {"symbol": symbol, "form": form, "data": []}