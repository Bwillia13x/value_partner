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

# Top-level tabs
tab_names = ["Intrinsic Value", "EPV vs Asset Cost", "Quality Heatmap", "Data"]
tabs = st.tabs(tab_names)

# -----------------------------------------------------------------------
# 1. Intrinsic Value – moved into first tab
# -----------------------------------------------------------------------

with tabs[0]:
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

# -----------------------------------------------------------------------
# 2. Greenwald EPV vs Asset Reproduction scatter
# -----------------------------------------------------------------------

with tabs[1]:
    st.header("🆚 EPV vs Asset Reproduction Cost")
    st.write("Scatter plot comparing Earnings Power Value (EPV) to Asset Reproduction cost.")

    symbol_list = st.text_area("Symbols (comma-separated)", "AAPL,MSFT,GOOG").split(",")
    show_button = st.button("Load EPV Data", key="epv_btn")

    if show_button:
        import altair as alt  # type: ignore
        import pandas as pd  # type: ignore
        from random import uniform  # placeholder for DB pull

        records = []
        for s in map(str.strip, symbol_list):
            if not s:
                continue
            # TODO: fetch from DB; random placeholder for now
            epv_val = uniform(50, 200)
            asset_cost = uniform(40, 220)
            records.append({"Symbol": s.upper(), "EPV": epv_val, "AssetCost": asset_cost})

        df = pd.DataFrame(records)
        chart = (
            alt.Chart(df)
            .mark_circle(size=100)
            .encode(x="AssetCost:Q", y="EPV:Q", tooltip=["Symbol", "EPV", "AssetCost"], color="Symbol")
            .properties(height=400)
        )
        st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------
# 3. Quality of Earnings heatmap
# -----------------------------------------------------------------------

with tabs[2]:
    st.header("🔬 Quality of Earnings Heat-Map")
    st.write("Visualise manipulation and quality scores across your watch-list.")

    watch_symbols = st.text_input("Watch-list symbols", "AAPL,MSFT,TSLA").split(",")
    if st.button("Load Quality Scores"):
        import altair as alt  # type: ignore
        import pandas as pd  # type: ignore
        from random import uniform

        rows = []
        for s in map(str.strip, watch_symbols):
            if not s:
                continue
            rows.append(
                {
                    "Symbol": s.upper(),
                    "Piotroski": uniform(0, 9),
                    "Beneish": uniform(-3, -1),
                    "Sloan": uniform(-0.2, 0.2),
                    "AltmanZ": uniform(0, 4),
                }
            )

        df = pd.DataFrame(rows).set_index("Symbol")
        melt = df.reset_index().melt(id_vars=["Symbol"], var_name="Metric", value_name="Score")
        heat = (
            alt.Chart(melt)
            .mark_rect()
            .encode(
                x="Metric:N",
                y="Symbol:N",
                color=alt.Color("Score:Q", scale=alt.Scale(scheme="redyellowgreen")),
                tooltip=["Score"],
            )
            .properties(height=300)
        )
        st.altair_chart(heat, use_container_width=True)

# -----------------------------------------------------------------------
# 4. Existing Data section moves to tabs[3]
# -----------------------------------------------------------------------
with tabs[3]:
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