"""train.py

Dummy training script for Phase-1 demonstration. Logs a simple value-factor model metric to MLflow.
"""
from __future__ import annotations

import argparse
import tempfile

import mlflow
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=100)
    args = parser.parse_args()

    mlflow.set_experiment("demo-value-model")
    with mlflow.start_run():
        mlflow.log_param("n_estimators", args.n_estimators)
        # Simulate training outcome
        ir = np.random.uniform(0.3, 0.8)
        mlflow.log_metric("information_ratio", ir)
        # Save dummy model artifact
        with tempfile.NamedTemporaryFile("w", delete=False) as fp:
            fp.write("dummy model artifact")
            mlflow.log_artifact(fp.name, artifact_path="model")


if __name__ == "__main__":
    main()