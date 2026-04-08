"""
database.py
────────────
SQLAlchemy engine, session factory, and FastAPI DB dependency.

Startup sequence (called from main.py lifespan):
  1. create_schemas() — CREATE SCHEMA IF NOT EXISTS for each PG schema
  2. Base.metadata.create_all() — creates tables from all imported models
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schemas():
    """
    Ensure all required PostgreSQL schemas exist.
    Called once from main.py lifespan before create_all().
    """
    with engine.connect() as conn:
        for schema in ("mdm", "twam", "payment", "shipment", "auth", "email"):
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()