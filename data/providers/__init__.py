"""Data provider abstraction for production data sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class BaseProvider(ABC):
    """Abstract base provider."""

    @abstractmethod
    def fetch_fundamentals(self, tickers: List[str]) -> pd.DataFrame:  # noqa: D401
        """Return DataFrame of fundamentals."""