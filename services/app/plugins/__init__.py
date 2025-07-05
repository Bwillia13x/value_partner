"""Plugin architecture for marketplace models.
Plugins must expose `predict(payload: dict) -> dict`.
"""
from __future__ import annotations

import importlib
from importlib.metadata import entry_points
from typing import Dict, Callable

PLUGIN_GROUP = "valueinvest.plugins"


def load_plugins() -> Dict[str, Callable[[dict], dict]]:
    plugins = {}
    try:
        eps = entry_points(group=PLUGIN_GROUP)
        for entry in eps:
            module = entry.load()
            plugins[entry.name] = getattr(module, "predict")
    except Exception:
        pass
    # add built-in example plugin
    try:
        from app.plugins import example_plugin

        plugins["example_plugin"] = example_plugin.predict
    except Exception:
        pass
    return plugins

# load at import time
PLUGINS = load_plugins()