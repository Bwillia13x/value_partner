import pandas as pd

from models.src.factors import compute_factors


def test_compute_factors_basic():
    df = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "pe_ratio": [10, 20],
            "pb_ratio": [1, 2],
            "ev_ebitda": [5, 10],
            "roe": [0.15, 0.10],
            "de_ratio": [0.3, 0.6],
        }
    )
    out = compute_factors(df)
    assert "earnings_yield" in out.columns
    assert "value_score" in out.columns
    # Earnings yield should be inverse P/E
    assert out.loc[0, "earnings_yield"] == 0.1
    assert out.loc[1, "earnings_yield"] == 0.05