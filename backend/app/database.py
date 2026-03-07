"""
SUPERNATURAL - Database Configuration
SQLAlchemy engine & session factory
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Render provides postgres:// but SQLAlchemy 2.0 requires postgresql://
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Create engine (supports both SQLite dev & PostgreSQL prod)
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, ensures closure after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

