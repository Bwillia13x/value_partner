import os
from typing import Any, Dict

import requests

from .base import DataProvider


class AlphaVantageProvider(DataProvider):
    """Fetch data from Alpha Vantage (https://www.alphavantage.co)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY environment variable is required for AlphaVantageProvider")

    def fetch(self, symbol: str, function: str = "TIME_SERIES_DAILY_ADJUSTED") -> Dict[str, Any]:
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": "compact",
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()