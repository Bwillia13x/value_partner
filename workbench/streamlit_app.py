"""streamlit_app.py

Phase-3 UX workbench – Streamlit application to explore factor datasets and backtest outputs.
Run with: `streamlit run workbench/streamlit_app.py`
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

FACTOR_PATH = Path("data/samples/factors.parquet")
BACKTEST_PATH = Path("models/backtester/results/cumulative_returns.csv")

st.set_page_config(page_title="Value Factors Workbench", layout="wide")

# Main navigation
st.title("📊 Value Investing Workbench")

# ---------------------------------------------------------------------------
# Intrinsic Value panel
# ---------------------------------------------------------------------------

with st.expander("💰 Intrinsic Value Panel", expanded=True):
    col1, col2 = st.columns([1, 2])

    with col1:
        symbol = st.text_input("Ticker", value="AAPL", max_chars=8)

        # Parameter sliders
        discount_rate = st.slider("WACC / Discount Rate (%)", min_value=4.0, max_value=15.0, value=10.0, step=0.5) / 100
        terminal_growth = st.slider("Terminal Growth (%)", min_value=0.0, max_value=5.0, value=3.0, step=0.25) / 100
        mos_pct = st.slider("Margin of Safety (%)", min_value=0.0, max_value=50.0, value=25.0, step=1.0) / 100

        calc_btn = st.button("Compute Intrinsic Value")

    with col2:
        if st.session_state.get("valuation") and not calc_btn:
            valuation = st.session_state["valuation"]
        elif calc_btn:
            # Simple forecast model – assume starting FCF 100 and 5yr constant 5% growth
            from models.valuation import discounted_cash_flow  # noqa: WPS433

            starting_fcf = 100.0
            growth_rate = 0.05
            cash_flows = [starting_fcf * ((1 + growth_rate) ** i) for i in range(1, 6)]

            base_iv = discounted_cash_flow(cash_flows, discount_rate, terminal_growth)
            bear_iv = base_iv * 0.8
            bull_iv = base_iv * 1.3

            # MOS adjusted value
            mos_value = base_iv * (1 - mos_pct)

            valuation = {
                "bear": bear_iv,
                "base": base_iv,
                "bull": bull_iv,
                "mos": mos_value,
            }
            st.session_state["valuation"] = valuation
        else:
            valuation = None

        if valuation:
            import altair as alt  # type: ignore  # noqa: WPS433
            import pandas as pd  # type: ignore  # noqa: WPS433

            val_df = pd.DataFrame(
                {
                    "Scenario": ["Bear", "Base", "Bull", "MOS"],
                    "Value": [
                        valuation["bear"],
                        valuation["base"],
                        valuation["bull"],
                        valuation["mos"],
                    ],
                }
            )

            st.subheader("Tornado Chart – Valuation Range")
            bar = (
                alt.Chart(val_df)
                .mark_bar()
                .encode(x="Value:Q", y=alt.Y("Scenario:N", sort="-x"), tooltip=["Value"])
                .properties(height=200)
            )
            st.altair_chart(bar, use_container_width=True)

            # Historical intrinsic vs price placeholder chart
            st.subheader("Historical Intrinsic vs Market Price (placeholder)")
            # Simulate last 5 observations
            hist_df = pd.DataFrame(
                {
                    "Year": list(range(2019, 2024)),
                    "Intrinsic": [valuation["base"] * (0.8 + 0.05 * i) for i in range(5)],
                    "Price": [valuation["base"] * (0.9 + 0.04 * i) for i in range(5)],
                }
            )
            chart = (
                alt.Chart(hist_df.melt("Year", var_name="Series", value_name="Value"))
                .mark_line(point=True)
                .encode(x="Year:O", y="Value:Q", color="Series:N")
            )
            st.altair_chart(chart, use_container_width=True)

# Sidebar file selectors
factor_file = st.sidebar.text_input("Factors file", value=str(FACTOR_PATH))
backtest_file = st.sidebar.text_input("Backtest results", value=str(BACKTEST_PATH))

# Load data
if Path(factor_file).exists():
    factors_df = pd.read_parquet(factor_file)
    st.subheader("Factor Dataset")
    st.write(f"Rows: {len(factors_df):,}")
    sel_cols = st.multiselect(
        "Select columns to view", factors_df.columns.tolist(), default=["ticker", "value_score", "quality_score", "vq_score"]
    )
    st.dataframe(factors_df[sel_cols].head(200))
else:
    st.warning("Factor file not found. Generate it by running compute_factors_script.py")

if Path(backtest_file).exists():
    bt = pd.read_csv(backtest_file, parse_dates=["date"], index_col="date")
    st.subheader("Backtest Cumulative Returns")
    st.line_chart(bt)
else:
    st.warning("Backtest results not found. Run sample_backtest.py first.")