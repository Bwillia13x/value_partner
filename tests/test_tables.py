import os
from sqlalchemy import inspect

# Ensure in-memory SQLite for testing if not provided
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from services.db import init_db  # noqa: E402
from services.db.database import engine  # noqa: E402


def test_core_tables_exist():
    # Create tables
    init_db()

    inspector = inspect(engine)
    expected_tables = {
        "financial_statements",
        "key_metrics",
        "intrinsic_valuations",
        "qualitative_signals",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))