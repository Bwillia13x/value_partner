"""train_ensemble_optuna.py

Hyperparameter tuning of ensemble model using Optuna, logs each trial to MLflow.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import mlflow
import numpy as np
import optuna
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, StackingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

FACTOR_FILE = Path("data/samples/factors.parquet")


def load_data():
    df = pd.read_parquet(FACTOR_FILE)
    rng = np.random.default_rng(42)
    df["fwd_return"] = rng.normal(loc=0.01 + 0.05 * df["vq_score"], scale=0.05)
    features = [
        "earnings_yield",
        "book_to_market",
        "ev_ebitda_inverse",
        "quality_score",
        "vq_score",
    ]
    X_train, X_test, y_train, y_test = train_test_split(
        df[features], df["fwd_return"], test_size=0.2, random_state=1
    )
    return X_train, X_test, y_train, y_test


def objective(trial: optuna.Trial):
    X_train, X_test, y_train, y_test = load_data()

    rf_n = trial.suggest_int("rf_n_estimators", 100, 500)
    gbr_lr = trial.suggest_float("gbr_learning_rate", 0.01, 0.3, log=True)
    gbr_depth = trial.suggest_int("gbr_max_depth", 2, 6)

    estimators = [
        (
            "rf",
            RandomForestRegressor(
                n_estimators=rf_n, random_state=1, n_jobs=-1, max_depth=None
            ),
        ),
        (
            "gbr",
            GradientBoostingRegressor(
                learning_rate=gbr_lr, max_depth=gbr_depth, random_state=1
            ),
        ),
    ]

    model = StackingRegressor(
        estimators=estimators, final_estimator=LinearRegression(), passthrough=True, n_jobs=-1
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    score = r2_score(y_test, preds)
    mlflow.log_metric("r2", score)
    return -score  # minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20)
    args = parser.parse_args()

    mlflow.set_experiment("ensemble-optuna")
    with mlflow.start_run():
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=args.trials)
        mlflow.log_params(study.best_params)
        mlflow.log_metric("best_score", -study.best_value)
        print("Best R2:", -study.best_value)
        print("Best params:", study.best_params)


if __name__ == "__main__":
    main()