#!/usr/bin/env python3
"""Quick smoke test for the Value Partner platform.

This script assumes the FastAPI service is running locally on port 8000
and (optionally) that Redis/Celery are up. It performs a few basic
checks to verify that core endpoints respond as expected.

Usage:
    $ python scripts/smoke_test.py

Exit status will be non-zero on failure so you can integrate it into CI.
"""
from __future__ import annotations

import sys
import json
import textwrap
from typing import Any, Tuple

import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 5  # seconds


def request(
    method: str, endpoint: str, **kwargs: Any
) -> Tuple[bool, str | dict[str, Any]]:
    """Helper to perform an HTTP request and return (success, response)."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        if "application/json" in response.headers.get("content-type", ""):  # pragma: no cover
            return True, response.json()
        return True, response.text
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def banner(title: str) -> None:
    print("\n" + title)
    print("=" * len(title))


def main() -> None:  # pragma: no cover
    failures: list[str] = []

    banner("1. Health Check")
    ok, res = request("get", "/health")
    print("Result:", "PASS" if ok else "FAIL", "-", res)
    if not ok:
        failures.append("/health endpoint failed")
        sys.exit(1)  # Can't proceed without healthy service

    banner("2. Factors Endpoint (sample)")
    ok, res = request("get", "/data/factors?limit=1")
    print("Result:", "PASS" if ok else "FAIL")
    if ok:
        print(textwrap.shorten(json.dumps(res)[:250], width=120))
    else:
        failures.append("/data/factors endpoint failed")

    banner("3. Plugins Listing")
    ok, res = request("get", "/plugins")
    print("Result:", "PASS" if ok else "FAIL", "-", res)
    if not ok:
        failures.append("/plugins endpoint failed")
    else:
        plugins = res.get("available_plugins") if isinstance(res, dict) else None
        if plugins:
            plugin = plugins[0]
            banner(f"4. Execute Plugin: {plugin}")
            ok, run_res = request("post", "/plugins/run", json={"plugin": plugin, "payload": {}})
            print("Result:", "PASS" if ok else "FAIL", "-", run_res)
            if not ok:
                failures.append(f"/plugins/run for {plugin} failed")

    banner("Summary")
    if failures:
        print("❌ Smoke test finished with failures:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("✅ All tests passed!")


if __name__ == "__main__":
    main()
