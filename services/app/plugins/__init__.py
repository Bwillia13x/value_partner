"""Plugin architecture for marketplace models.
Plugins must expose `predict(payload: dict) -> dict`.
"""
from __future__ import annotations

import importlib
import pkg_resources
from typing import Dict, Callable

PLUGIN_GROUP = "valueinvest.plugins"


def load_plugins() -> Dict[str, Callable[[dict], dict]]:
    plugins = {}
    for entry in pkg_resources.iter_entry_points(group=PLUGIN_GROUP):
        module = entry.load()
        plugins[entry.name] = getattr(module, "predict")
    # add built-in example plugin
    try:
        from services.app.plugins import example_plugin

        plugins["example_plugin"] = example_plugin.predict
    except Exception:
        pass
    return plugins

# load at import time
PLUGINS = load_plugins()