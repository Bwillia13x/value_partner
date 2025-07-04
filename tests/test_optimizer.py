import numpy as np
import pandas as pd
from models.optimizer.mean_variance import mv_weights


def test_mv_weights():
    # Two-asset example: asset A higher return, same variance, expect positive weight tilt
    rng = np.random.default_rng(0)
    ret = pd.DataFrame({
        "A": rng.normal(0.02, 0.05, size=120),
        "B": rng.normal(0.01, 0.05, size=120),
    })
    w = mv_weights(ret)
    assert w["A"] > w["B"]
    # Weights should sum to 1
    assert abs(w.sum() - 1) < 1e-9