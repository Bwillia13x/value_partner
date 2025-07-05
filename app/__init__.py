"""Compatibility shim for tests that import the top-level `app` package.

In production code, our FastAPI application lives under `services.app`.
However, some legacy tests expect `import app.*` to work. This module
re-exports everything from `services.app` to satisfy those imports while
avoiding duplication.
"""
from __future__ import annotations

import importlib
import sys as _sys

# Import the real application package
_real_app = importlib.import_module("services.app")

# Re-export its public attributes (excluding dunders)
for _name in dir(_real_app):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_real_app, _name)

# Ensure that `sys.modules["app"]` points to this shim so subsequent
# imports get the same module instance.
_sys.modules[__name__] = _real_app  # type: ignore
