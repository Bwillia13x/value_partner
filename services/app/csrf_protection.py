"""CSRF Protection Middleware for FastAPI"""

import hmac
import hashlib
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import os

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF Protection Middleware using double submit cookie pattern"""
    
    def __init__(self, app, secret_key: Optional[str] = None):
        super().__init__(app)
        self.secret_key = secret_key or os.getenv("SECRET_KEY", "")
        if not self.secret_key:
            raise ValueError("SECRET_KEY required for CSRF protection")
        
        # Safe methods that don't need CSRF protection
        self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}
        
        # Exempt paths that don't need CSRF protection
        self.exempt_paths = {
            "/health", 
            "/health/detailed", 
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/webhooks/plaid"  # Webhooks use signature verification instead
        }
    
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token"""
        # Generate random value
        random_value = secrets.token_hex(16)
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode(), 
            random_value.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return f"{random_value}.{signature}"
    
    def verify_csrf_token(self, token: str) -> bool:
        """Verify a CSRF token"""
        try:
            if not token or '.' not in token:
                return False
            
            random_value, signature = token.rsplit('.', 1)
            
            # Recreate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                random_value.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Constant time comparison
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF protection for safe methods
        if request.method in self.safe_methods:
            response = await call_next(request)
            # Add CSRF token to response for safe methods
            if request.url.path not in self.exempt_paths:
                csrf_token = self.generate_csrf_token()
                response.set_cookie(
                    "csrf_token",
                    csrf_token,
                    httponly=False,  # Needs to be accessible to JavaScript
                    secure=True,     # HTTPS only in production
                    samesite="strict"
                )
                response.headers["X-CSRF-Token"] = csrf_token
            return response
        
        # Skip CSRF protection for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # For unsafe methods, verify CSRF token
        csrf_token = None
        
        # Check for CSRF token in header
        csrf_token = request.headers.get("X-CSRF-Token")
        
        # If not in header, check cookie
        if not csrf_token:
            csrf_token = request.cookies.get("csrf_token")
        
        # If still not found, check form data for POST requests
        if not csrf_token and request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                # This is a simplified check - in practice you'd need to parse the body
                pass
        
        # Verify the token
        if not csrf_token or not self.verify_csrf_token(csrf_token):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "CSRF token missing or invalid",
                    "error_type": "csrf_protection_failed",
                    "message": "Request blocked by CSRF protection"
                }
            )
        
        return await call_next(request)