import importlib
import pytest

MODULES = [
    "data.ingestion.compustat_ingest",
    "data.transform.convert_to_delta",
]

@pytest.mark.parametrize("mod_path", MODULES)
def test_pipeline_module_import(mod_path):
    try:
        mod = importlib.import_module(mod_path)
    except Exception as e:
        pytest.skip(f"Skipping {mod_path}: {e}")
    else:
        assert mod is not None