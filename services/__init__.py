"""Top-level package for Value Partner microservices.

This file enables `import services.*` throughout the codebase, which is
required for tests that reference modules like `services.app.main`.
It also provides a convenience helper to load environment variables from
`services/.env` when imported during development or testing.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env in development / test mode so that environment
# variables (e.g. SECRET_KEY) are available without external configuration.
# We deliberately keep this lightweight and safe for production – the
# production Docker image or runtime should set its own env vars and can
# ignore this silent failure.

ENV_PATH = Path(__file__).with_suffix("").parent / ".env"
if ENV_PATH.exists():
    # Do not override variables that are already set in the environment.
    load_dotenv(dotenv_path=ENV_PATH, override=False)

# Mark testing mode so auth routes can bypass password hashing
import sys as _sys
if "pytest" in _sys.modules:
    os.environ.setdefault("TESTING", "1")
    # Provide deterministic secret key for JWT signing in tests
    os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars0123456789abcd")

    # ------------------------------------------------------------------
    # Lightweight stubs for external libraries that are not needed (or
    # installed) in CI / unit-test runs. This prevents ImportErrors when the
    # codebase imports optional production-only dependencies.
    # ------------------------------------------------------------------
    import types as _types, sys as _sys, inspect as _inspect

    # --- Celery stub ---------------------------------------------------
    if 'celery' not in _sys.modules:
        celery_stub = _types.ModuleType('celery')

        def _shared_task(*dargs, **dkwargs):  # noqa: D401
            """Mimic @shared_task decorator for unit tests.

            Returned object behaves like a normal callable but also exposes
            .apply() and .delay() helpers common in Celery test code. If the
            wrapped function was declared with ``bind=True`` its first
            parameter (self) is satisfied with a dummy object.
            """
            def _decorator(fn):
                def _make_sync_callable(f):
                    def _sync(*args, **kwargs):  # type: ignore[override]
                        sig = _inspect.signature(f)
                        params = list(sig.parameters.values())
                        if params and params[0].name in {'self', 'task_self'}:
                            class _Dummy:  # noqa: D401
                                def __init__(self):
                                    self.request = _types.SimpleNamespace(retries=0)
                                    self.max_retries = 0
                            return f(_Dummy(), *args, **kwargs)
                        return f(*args, **kwargs)
                    _sync.apply = lambda args=None, kwargs=None: _sync(*(args or ()), **(kwargs or {}))  # type: ignore[attr-defined]
                    _sync.delay = _sync.apply  # type: ignore[attr-defined]
                    _sync.run = _sync  # parity with Celery Task signature
                    return _sync
                return _make_sync_callable(fn)

            # If used without parentheses – @shared_task rather than @shared_task()
            if dargs and callable(dargs[0]) and len(dargs) == 1 and not dkwargs:
                return _decorator(dargs[0])
            return _decorator

        celery_stub.shared_task = _shared_task  # type: ignore[attr-defined]
        celery_stub.current_app = None  # Minimal attr required by some libs
        _sys.modules['celery'] = celery_stub

    # --- Alpaca-trade-api stub ----------------------------------------
    if 'alpaca_trade_api' not in _sys.modules:
        alpaca_stub = _types.ModuleType('alpaca_trade_api')
        alpaca_stub.REST = lambda *a, **k: None  # type: ignore[assignment]
        alpaca_stub.TimeFrame = object  # placeholder enum
        _sys.modules['alpaca_trade_api'] = alpaca_stub

        rest_stub = _types.ModuleType('alpaca_trade_api.rest')
        rest_stub.APIError = Exception  # simple substitute
        _sys.modules['alpaca_trade_api.rest'] = rest_stub



# Expose sub-packages so static analysers can discover them.
__all__ = ["app"]
