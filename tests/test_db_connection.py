from services.db.database import engine


def test_engine_url_is_set():
    assert engine.url is not None
    # Check URL scheme is postgres or sqlite for CI convenience
    assert engine.url.drivername in {"postgresql+psycopg2", "sqlite"}