from abc import ABC, abstractmethod


class DataProvider(ABC):
    """Common interface for all external data providers."""

    @abstractmethod
    def fetch(self, symbol: str, *args, **kwargs):
        """Fetch data for a given symbol and return normalized payload."""
        raise NotImplementedError