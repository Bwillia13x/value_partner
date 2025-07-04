from .base import Base
from .database import engine, SessionLocal
from . import models  # noqa


def init_db():
    """Initialize database tables. Call at startup if needed."""
    Base.metadata.create_all(bind=engine)