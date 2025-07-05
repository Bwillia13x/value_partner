"""
Integration modules for external services like Plaid, Alpaca, etc.

This package contains services and routes for integrating with external
financial data providers and brokerages.
"""

# Import services and routes to make them available when importing the package
from .plaid_service import PlaidService
_plaid_service_instance = None

def get_plaid_service() -> PlaidService:
    global _plaid_service_instance
    if _plaid_service_instance is None:
        _plaid_service_instance = PlaidService()
    return _plaid_service_instance

def set_plaid_service(service: PlaidService):
    global _plaid_service_instance
    _plaid_service_instance = service

# ---------------------------------------------------------------------------
# Lightweight in-memory stub for Alpaca integration (test/dummy-friendly)
# ---------------------------------------------------------------------------
try:
    from ..alpaca_service import AlpacaService as _RealAlpacaService  # type: ignore
except Exception:  # pragma: no cover – Alpaca SDK may be missing in dev env
    class _RealAlpacaService:  # pyright: ignore
        """Fallback Alpaca service with minimal surface for tests."""

        class _DummyAccount(dict):
            cash: float = 0.0

            def __init__(self, cash: float = 0.0):
                super().__init__()
                self.cash = cash

        class _DummyPosition(dict):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        # --- minimal API expected by reconciliation & other modules ---
        def get_account(self, access_token: str | None = None):  # noqa: D401
            """Return dummy account object with `cash` attribute."""
            return self._DummyAccount(cash=0.0)

        def get_positions(self, access_token: str | None = None):  # noqa: D401
            """Return empty list of positions for stubbed environment."""
            return []

        def sync_account_data(self, *args, **kwargs):  # noqa: D401
            return {"status": "stub", "detail": "Sync skipped in stub"}

    # Alias the stub so downstream code can import transparently
    AlpacaService = _RealAlpacaService  # type: ignore
else:
    AlpacaService = _RealAlpacaService  # type: ignore

# Singleton pattern mirroring Plaid implementation
_alpaca_service_instance: AlpacaService | None = None

def get_alpaca_service() -> AlpacaService:  # noqa: D401
    """Return global AlpacaService instance (stub or real)."""
    global _alpaca_service_instance
    if _alpaca_service_instance is None:
        _alpaca_service_instance = AlpacaService()
    return _alpaca_service_instance

def set_alpaca_service(service: AlpacaService):
    """Replace the global AlpacaService instance (for tests/mocking)."""
    global _alpaca_service_instance
    _alpaca_service_instance = service

# We are intentionally NOT instantiating services here to avoid circular imports
# and allow mocking in tests. They should be accessed via their respective get_service() or set_service() functions.

__all__ = [
    'PlaidService',
    'get_plaid_service',
    'set_plaid_service',
    "AlpacaService",
    "get_alpaca_service",
    "set_alpaca_service",
]











