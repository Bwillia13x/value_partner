import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set for production. Generate a secure key with: openssl rand -hex 32")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Password Hashing ---
import sys
TESTING_MODE = os.getenv("TESTING") == "1" or "pytest" in sys.modules

# In test mode, avoid bcrypt to speed up tests and prevent backend issues.
if TESTING_MODE:
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
else:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- JWT Token Handling ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new JWT access token.

    If ``expires_delta`` is omitted, the token will expire after
    ``ACCESS_TOKEN_EXPIRE_MINUTES`` (30) minutes by default.
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Token Verification ---

def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload if valid.

    Returns ``None`` if the token is invalid, expired, or malformed.
    """
    if not token or not isinstance(token, str):
        return None

    # Allow "Bearer <token>" format
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        # jose throws multiple exception classes; we don't need granularity here for tests
        return None

# --- Helpers for FastAPI-style dependency injection used in tests ---
from contextlib import contextmanager
from types import GeneratorType

try:
    from fastapi import HTTPException, status
except ImportError:
    # Provide minimal stubs so we don't add a hard dependency on FastAPI for unit tests
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail

    class status:
        HTTP_401_UNAUTHORIZED = 401

from services.app.database import get_db, User  # type: ignore


def _resolve_db(db_session):
    """Return a usable DB session from either injected argument or default dependency."""
    if db_session is not None:
        return db_session

    # get_db is a generator dependency
    db_gen = get_db()
    if isinstance(db_gen, GeneratorType):
        db = next(db_gen)
        return db
    return db_gen


def get_current_user(token: str, db_session=None):
    """Retrieve the current user based on the supplied JWT *token*.

    Mimics FastAPI's dependency signature so tests can call it directly.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token missing 'sub'")

    db = _resolve_db(db_session)

    if hasattr(User, "username"):
        user = db.query(User).filter((User.username == username) | (User.email == username)).first()
    else:
        user = db.query(User).filter(User.email == username).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_active_user(current_user):
    """Ensure that *current_user* is active, raising if not."""
    if getattr(current_user, "is_active", False):
        return current_user
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
