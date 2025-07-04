import os
from typing import Any, Dict

import requests

from .base import DataProvider


class TiingoProvider(DataProvider):
    """Fetch market data from Tiingo (https://api.tiingo.com)."""

    BASE_URL = "https://api.tiingo.com/tiingo"

    def __init__(self):
        self.api_key = os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY environment variable is required for TiingoProvider")

    def fetch(self, symbol: str, endpoint: str = "daily") -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}/{symbol}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()