import pandas as pd
from models.optimizer.transaction_cost import sqrt_impact, almgren_chriss_temp


def test_sqrt_impact():
    vols = pd.Series([0.0, 0.01, 0.04])
    costs = sqrt_impact(vols, k=0.2, daily_vol=0.03)
    assert costs.iloc[1] > 0
    assert costs.iloc[0] == 0


def test_almgren():
    shares = pd.Series([1000, 500])
    costs = almgren_chriss_temp(cost_per_share=0.001, eta=0.01, shares=shares, time_horizon=1.0)
    assert len(costs) == 2
    assert costs.iloc[0] > costs.iloc[1]