"""CompustatProvider implements BaseProvider by calling Compustat Datahub API (simplified)."""
from __future__ import annotations

import os
import sys
from typing import List

import pandas as pd
import requests

from data.providers import BaseProvider

BASE_URL = "https://api.compustat.com/v1/fundamentals"  # hypothetical


class CompustatProvider(BaseProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("COMPUSTAT_API_KEY")
        if not self.api_key:
            raise RuntimeError("COMPUSTAT_API_KEY not set for CompustatProvider")
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def fetch_fundamentals(self, tickers: List[str]) -> pd.DataFrame:
        dfs = []
        for t in tickers:
            url = f"{BASE_URL}/{t}"
            try:
                resp = requests.get(url, headers=self.headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                dfs.append(pd.json_normalize(data))
            except Exception as e:
                print(f"Error fetching {t}: {e}", file=sys.stderr)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()