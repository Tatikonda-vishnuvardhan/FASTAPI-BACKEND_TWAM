"""
database.py
────────────
SQLAlchemy session setup.

CHANGE: Schema creation moved OUT of module-level code into
app lifespan startup event in main.py.
This prevents schema-creation running during tests/imports.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # detect stale connections
    pool_size=10,            # connection pool size
    max_overflow=20,         # extra connections under load
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
    Create required PostgreSQL schemas.
    Called ONCE from main.py lifespan — not on import.
    """
    with engine.connect() as conn:
        for schema in ("mdm", "twam", "payment", "shipment", "auth", "email"):
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()


def run_migrations():
    """
    Idempotent column-level migrations run after create_all().
    Uses information_schema so each ALTER is skipped if the column
    already exists — safe to run on every startup.
    """
    migrations = [
        # ProductReview: optional user photo for testimonial display
        {
            "schema": "twam",
            "table":  "ProductReview",
            "column": "Photo",
            "type":   "VARCHAR",
        },
        # Products: stock number field added to model after initial table creation
        {
            "schema": "twam",
            "table":  "Products",
            "column": "StockNo",
            "type":   "VARCHAR",
        },
    ]

    with engine.connect() as conn:
        for m in migrations:
            exists = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = :schema "
                    "  AND table_name   = :table "
                    "  AND column_name  = :column"
                ),
                {"schema": m["schema"], "table": m["table"], "column": m["column"]},
            ).fetchone()

            if not exists:
                conn.execute(
                    text(
                        f'ALTER TABLE {m["schema"]}."{m["table"]}" '
                        f'ADD COLUMN "{m["column"]}" {m["type"]} NULL'
                    )
                )
        conn.commit()