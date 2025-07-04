import pandas as pd
from models.src.momentum import compute_momentum


def test_momentum():
    data = {
        "date": pd.date_range("2020-01-31", periods=14, freq="M").tolist() * 1,
        "ticker": ["AAA"] * 14,
        "price": list(range(1, 15)),
    }
    df = pd.DataFrame(data)
    out = compute_momentum(df, lookback=12, skip=1)
    # Momentum appears starting at row 13 (index 12)
    mom_col = "mom_12_1"
    assert mom_col in out.columns
    # For line index 13 (price 14, shifted 1 month price 13, lagged 13-1=1 -> price 1), mom = 13/1 -1 =12
    val = out.loc[13, mom_col]
    assert abs(val - 12) < 1e-6