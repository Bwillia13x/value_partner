from services.app.data_providers.sec_edgar import SecEdgarProvider
from .celery_app import app

provider = SecEdgarProvider()


@app.task(name="services.app.tasks.data_acquisition.nightly_download")
def nightly_download():
    symbols = ["AAPL", "MSFT"]  # TODO: pull from watchlist/DB
    for symbol in symbols:
        provider.fetch(symbol)
    return f"Downloaded data for {len(symbols)} symbols"