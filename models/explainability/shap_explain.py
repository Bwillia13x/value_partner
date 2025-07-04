"""shap_explain.py

Compute SHAP values for the latest ensemble model run stored in MLflow and
save a summary plot to `models/explainability/shap_summary.png`.

Prerequisites: run `train_ensemble.py` first and ensure MLflow tracking URI is set.
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import shap

FACTOR_PATH = Path("data/samples/factors.parquet")
OUTPUT_PATH = Path("models/explainability/shap_summary.png")


def load_latest_model() -> mlflow.pyfunc.PyFuncModel:  # type: ignore
    client = mlflow.tracking.MlflowClient()
    experiments = client.search_experiments(filter_string="name = 'ensemble-value-model'")
    if not experiments:
        raise RuntimeError("No ensemble-value-model experiment found")

    exp_id = experiments[0].experiment_id
    runs = client.search_runs(exp_id, order_by=["attribute.end_time DESC"], max_results=1)
    if not runs:
        raise RuntimeError("No runs in ensemble-value-model experiment")
    run_id = runs[0].info.run_id
    model_uri = f"runs:/{run_id}/model"
    return mlflow.pyfunc.load_model(model_uri)


def main():
    model = load_latest_model()
    df = pd.read_parquet(FACTOR_PATH).sample(500, random_state=1)
    feature_cols = model.metadata.get("signature").inputs.column_names  # type: ignore
    X = df[feature_cols]

    explainer = shap.Explainer(model.predict, X)
    shap_values = explainer(X)
    shap.plots.beeswarm(shap_values, show=False)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    shap.plots.beeswarm(shap_values, show=False)
    import matplotlib.pyplot as plt

    plt.title("SHAP Summary – Ensemble Value Model")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH)
    print(f"Saved SHAP summary plot to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()