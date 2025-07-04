import pandas as pd
from models.analytics.gips import gips_metrics


def test_gips_metrics():
    returns = pd.Series([0.01] * 12)  # +1% each month
    metrics = gips_metrics(returns)
    # total return (1.01^12 -1) ~12.68%
    assert abs(metrics["total_return"] - (1.01**12 - 1)) < 1e-6
    # sharpe positive
    assert metrics["sharpe"] > 0