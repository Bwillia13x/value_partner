import os
from typing import Any, Dict

from .base import DataProvider


class TranscriptsProvider(DataProvider):
    """Fetch earnings call transcripts from Symbl.ai or SeekingAlpha (stub)."""

    def __init__(self):
        self.symbl_token = os.getenv("SYMBL_APP_TOKEN")
        self.sa_key = os.getenv("SEEKINGALPHA_API_KEY")
        if not (self.symbl_token or self.sa_key):
            raise ValueError(
                "Provide SYMBL_APP_TOKEN or SEEKINGALPHA_API_KEY for TranscriptsProvider"
            )

    def fetch(self, symbol: str, source: str = "symbl") -> Dict[str, Any]:
        if source == "symbl":
            # TODO: Implement Symbl.ai conversation transcripts retrieval
            return {"symbol": symbol, "transcripts": [], "source": "symbl"}
        # TODO: Implement SeekingAlpha transcript scraping/API once available
        return {"symbol": symbol, "transcripts": [], "source": "seekingalpha"}