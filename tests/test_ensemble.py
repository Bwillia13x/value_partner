from models.ensembles.train_ensemble import load_dataset


def test_load_dataset():
    df = load_dataset()
    assert "fwd_return" in df.columns
    assert not df.empty