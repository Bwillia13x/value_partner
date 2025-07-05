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

# --- Helpers for FastAPI-style dependency injection ---
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session # Added
from types import GeneratorType # Added

from services.app.database import get_db, User  # type: ignore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # Relative to app root

def _resolve_db(db_session, db_dependency: Session = Depends(get_db)): # Added db_dependency
    """Return a usable DB session from either injected argument or default dependency."""
    if db_session is not None:
        return db_session
    return db_dependency


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)): # Modified
    """
    Retrieve the current user based on the supplied JWT token from OAuth2PasswordBearer.
    This is intended for use as a FastAPI dependency.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if not payload:
        raise credentials_exception

    username_or_email = payload.get("sub")
    if username_or_email is None:
        raise credentials_exception

    # db = _resolve_db(db_session, db) # db is already resolved by Depends(get_db)

    if hasattr(User, "username"): # Check if User model has a username field
        user = db.query(User).filter((User.username == username_or_email) | (User.email == username_or_email)).first()
    else: # Fallback to email only if no username field
        user = db.query(User).filter(User.email == username_or_email).first()

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)): # Modified
    """Ensure that current_user is active, raising if not."""
    if not getattr(current_user, "is_active", True): # Default to True if is_active is not present, or check its value
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user
