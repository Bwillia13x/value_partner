import os
from typing import Any, Dict, List
from .base import DataProvider

try:
    from sec_api import QueryApi
except ImportError:  # pragma: no cover
    QueryApi = None  # type: ignore


class SecEdgarProvider(DataProvider):
    """Fetch filings from SEC Edgar using the sec-api.com service.

    Set the environment variable `SEC_API_KEY` with your API key obtained from https://sec-api.io.
    """

    def __init__(self):
        self.api_key = os.getenv("SEC_API_KEY")
        if QueryApi is None:
            raise ImportError(
                "sec-api package is not installed. Add `sec-api` to requirements and reinstall."
            )
        if not self.api_key:
            raise ValueError("SEC_API_KEY environment variable is required for SecEdgarProvider")
        self.query_api = QueryApi(api_key=self.api_key)

    def fetch(self, symbol: str, form: str = "10-K", limit: int = 1) -> Dict[str, Any]:
        """Return a JSON dict of recent filings.

        Arguments:
            symbol: Stock ticker symbol.
            form: Filing form type (e.g., 10-K, 10-Q, 8-K).
            limit: How many filings to retrieve.
        """
        query = {
            "query": {
                "query_string": {
                    "query": f"ticker:{symbol} AND formType:{form}",
                }
            },
            "from": "0",
            "size": str(limit),
            "sort": [{"filedAt": {"order": "desc"}}],
        }
        filings: Dict[str, Any] = self.query_api.get_filings(query)
        return filings