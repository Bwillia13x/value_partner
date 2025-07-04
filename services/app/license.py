"""license.py
FastAPI middleware to enforce license tiers and rate limits.
For demo, reads `X-API-Tier` header: `free`, `pro`, `enterprise`.
Limits: free=10 req/min, pro=60 req/min, enterprise=unlimited.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

RATE_LIMITS = {"free": 10, "pro": 60, "enterprise": float("inf")}


class LicenseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window = 60  # seconds
        self.calls: Dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        tier = request.headers.get("X-API-Tier", "free")
        limit = RATE_LIMITS.get(tier, 10)
        ip = request.client.host
        now = time.time()
        calls = self.calls[ip]
        # purge old
        self.calls[ip] = [t for t in calls if now - t < self.window]
        if len(self.calls[ip]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded for tier")
        self.calls[ip].append(now)
        return await call_next(request)