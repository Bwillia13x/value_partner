import pandas as pd
import numpy as np
from models.backtester.backtester import Backtester


def create_dummy_df():
    dates = pd.date_range("2021-01-31", periods=3, freq="M")
    tickers = ["AAA", "BBB", "CCC"]
    rows = []
    rng = np.random.default_rng(1)
    for date in dates:
        for ticker in tickers:
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "return": rng.normal(0.01, 0.05),
                    "value_score": rng.normal(),
                }
            )
    return pd.DataFrame(rows)


def test_backtester_runs():
    df = create_dummy_df()
    bt = Backtester("value_score", n_quantiles=3)
    cum = bt.run(df)
    assert not cum.empty
    assert "Q1" in cum.columns
    stats = bt.performance_stats(cum["Q1"])
    assert "sharpe" in stats