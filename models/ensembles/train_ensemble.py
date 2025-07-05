"""train_ensemble.py

Phase-3 machine-learning ensemble demonstration.
Loads factor dataset produced earlier, splits train/test, trains stacking regressor predicting next-month returns.
Logs results to MLflow.
"""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    import mlflow  # type: ignore
except ImportError:  # pragma: no cover – provide no-op stub
    class _MLFlowStub:
        def __getattr__(self, item):
            # Return callable no-op to swallow any mlflow calls used in script
            def _no_op(*args, **kwargs):
                return None
            return _no_op
    mlflow = _MLFlowStub()  # type: ignore

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, StackingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

FACTOR_FILE = Path("data/samples/factors.parquet")


def load_dataset() -> pd.DataFrame:
    df = pd.read_parquet(FACTOR_FILE)
    # For demo, create synthetic 1-month ahead returns target
    rng = np.random.default_rng(42)
    df["fwd_return"] = rng.normal(loc=0.01 + 0.05 * df["vq_score"], scale=0.05)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_size", type=float, default=0.2)
    args = parser.parse_args()

    df = load_dataset()
    features = [
        "earnings_yield",
        "book_to_market",
        "ev_ebitda_inverse",
        "quality_score",
        "vq_score",
    ]
    X = df[features]
    y = df["fwd_return"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_size, random_state=1)

    estimators = [
        ("rf", RandomForestRegressor(n_estimators=200, random_state=1)),
        ("gbr", GradientBoostingRegressor(random_state=1)),
    ]
    stack = StackingRegressor(
        estimators=estimators,
        final_estimator=LinearRegression(),
        passthrough=True,
        n_jobs=-1,
    )

    mlflow.set_experiment("ensemble-value-model")
    with mlflow.start_run():
        stack.fit(X_train, y_train)
        preds = stack.predict(X_test)
        score = r2_score(y_test, preds)
        mlflow.log_metric("r2", score)
        mlflow.sklearn.log_model(stack, artifact_path="model")
        print(f"Test R^2: {score:.4f}")


if __name__ == "__main__":
    main()