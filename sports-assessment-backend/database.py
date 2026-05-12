"""
database.py
-----------
SQLAlchemy engine and session factory for the SQLite-backed simulated database.
Using SQLite for local-first operation; swap DATABASE_URL for Postgres in production.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./assessment.db"

# Ensure single-thread check is disabled for SQLite used with multiple async workers
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set True to see SQL logs during dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_safe_schema_updates():
    """
    Apply additive SQLite schema updates for backwards compatibility.
    This avoids runtime 500s when new nullable columns are introduced.
    """
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())

        if "athletes" in table_names:
            cols = {c["name"] for c in inspector.get_columns("athletes")}
            if "user_id" not in cols:
                conn.execute(text("ALTER TABLE athletes ADD COLUMN user_id TEXT"))
