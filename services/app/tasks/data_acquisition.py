from datetime import datetime
from typing import List, Type

from .celery_app import app
from services.app.storage.s3 import generate_key, put_json
from services.app.data_providers import (
    SecEdgarProvider,
    FMPProvider,
    AlphaVantageProvider,
    TiingoProvider,
    PolygonProvider,
    TranscriptsProvider,
    OwnershipProvider,
)
from services.app.data_providers.base import DataProvider


PROVIDER_CLASSES: List[Type[DataProvider]] = [
    SecEdgarProvider,
    FMPProvider,
    AlphaVantageProvider,
    TiingoProvider,
    PolygonProvider,
    TranscriptsProvider,
    OwnershipProvider,
]


@app.task(name="services.app.tasks.data_acquisition.nightly_download")
def nightly_download() -> str:
    """Download fresh data for a watchlist of symbols and store raw payloads to S3."""
    symbols = ["AAPL", "MSFT"]  # TODO: pull dynamic list from DB or config
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    provider_instances: List[DataProvider] = []
    for cls in PROVIDER_CLASSES:
        try:
            provider_instances.append(cls())
        except Exception as exc:  # noqa: BLE001
            # Misconfigured provider (likely missing API key) – skip but log.
            print(f"Skipping provider {cls.__name__}: {exc}")

    for symbol in symbols:
        for provider in provider_instances:
            try:
                payload = provider.fetch(symbol)  # type: ignore[arg-type]
                if payload:
                    key = generate_key(symbol, provider.__class__.__name__, timestamp)
                    s3_uri = put_json(key, payload)
                    print(f"Stored {symbol} payload from {provider.__class__.__name__} to {s3_uri}")
            except Exception as exc:  # noqa: BLE001
                print(f"Error fetching {symbol} with {provider.__class__.__name__}: {exc}")

    return (
        f"Processed {len(symbols)} symbols with {len(provider_instances)} active providers"
    )