"""Compatibility re-export module for ORM models.

This module exists primarily for unit tests and legacy imports that expect
`services.app.models` to expose the SQLAlchemy ORM models. Internally, all
models are declared in `services.app.database`.  Importing them here keeps
those modules decoupled while preserving backwards-compatibility.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .database import (
    Base,
    User,
    Strategy,
    StrategyHolding,
    Account,
    Holding,
    Transaction,
    Portfolio,
    Custodian,
    get_db,
    init_db,
)

__all__: list[str] = [
    "Base",
    "User",
    "Strategy",
    "StrategyHolding",
    "Account",
    "Holding",
    "Transaction",
    "Portfolio",
    "Custodian",
    "get_db",
    "init_db",
]
