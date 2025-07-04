"""valueinvest_sdk client library.

Usage:
```python
from valueinvest_sdk import ValueInvestClient
client = ValueInvestClient(base_url="https://api.example.com", api_key="MY_KEY", tier="pro")
print(client.health())
print(client.copilot_query("Explain EPV"))
```
"""
from __future__ import annotations

import requests
from typing import List


class ValueInvestClient:
    def __init__(self, base_url: str, api_key: str | None = None, tier: str = "free"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-API-Tier": tier})
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    # Utility -----------------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # Public endpoints ---------------------------------------------------------
    def health(self) -> dict:
        resp = self.session.get(self._url("/health"))
        resp.raise_for_status()
        return resp.json()

    def copilot_query(self, question: str) -> List[str]:
        resp = self.session.post(self._url("/copilot/query"), json={"question": question})
        resp.raise_for_status()
        return resp.json()["answers"]

    def list_plugins(self) -> List[str]:
        resp = self.session.get(self._url("/plugins"))
        resp.raise_for_status()
        return resp.json()["available_plugins"]

    def run_plugin(self, name: str, payload: dict) -> dict:
        resp = self.session.post(self._url("/plugins/run"), json={"plugin": name, "payload": payload})
        resp.raise_for_status()
        return resp.json()["result"]