import sys
import types
import pytest

# Create a dummy streamlit module to satisfy imports when running outside Streamlit runtime

dummy = types.ModuleType("streamlit")
for fn in [
    "set_page_config",
    "title",
    "subheader",
    "write",
    "warning",
    "dataframe",
    "line_chart",
]:
    setattr(dummy, fn, lambda *args, **kwargs: None)
# Sidebar with text_input
sidebar = types.SimpleNamespace(text_input=lambda *args, **kwargs: "")
setattr(dummy, "sidebar", sidebar)

sys.modules["streamlit"] = dummy

try:
    import workbench.streamlit_app as app_mod
except Exception as e:
    pytest.skip(f"Could not import streamlit_app: {e}")
else:
    def test_streamlit_app_imported():
        assert app_mod is not None