import os
from typing import Any, Dict

import requests

from .base import DataProvider


class FMPProvider(DataProvider):
    """Fetch data from Financial Modeling Prep API (https://financialmodelingprep.com)."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable is required for FMPProvider")

    def fetch(self, symbol: str, endpoint: str = "profile") -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}/{symbol}?apikey={self.api_key}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()