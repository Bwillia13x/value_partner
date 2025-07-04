import os
from typing import Any, Dict

import requests

from .base import DataProvider


class OwnershipProvider(DataProvider):
    """Fetch insider & institutional ownership data (FMP endpoint stub)."""

    FMP_ENDPOINT = "institutional-ownership"
    BASE_URL = "https://financialmodelingprep.com/api/v4"

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable is required for OwnershipProvider")

    def fetch(self, symbol: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{self.FMP_ENDPOINT}?symbol={symbol}&apikey={self.api_key}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()