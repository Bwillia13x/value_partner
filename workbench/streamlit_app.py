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
st.title("📊 Value Investing Workbench")

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