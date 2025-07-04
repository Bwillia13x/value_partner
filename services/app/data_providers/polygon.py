import os
from typing import Any, Dict

import requests

from .base import DataProvider


class PolygonProvider(DataProvider):
    """Fetch market data from Polygon.io (https://polygon.io)."""

    BASE_URL = "https://api.polygon.io"

    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable is required for PolygonProvider")

    def fetch(self, symbol: str, endpoint: str = "/v3/reference/tickers") -> Dict[str, Any]:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        url = f"{self.BASE_URL}{path}/{symbol}?apiKey={self.api_key}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()