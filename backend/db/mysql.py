"""
MySQL connection using SQLAlchemy (sync) with PyMySQL.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config import settings

DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_pass}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    "?charset=utf8mb4"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fetch_one(db: Session, query: str, params: dict) -> dict | None:
    row = db.execute(text(query), params).mappings().first()
    return dict(row) if row else None


def fetch_all(db: Session, query: str, params: dict | None = None) -> list[dict]:
    rows = db.execute(text(query), params or {}).mappings().all()
    return [dict(r) for r in rows]


def execute(db: Session, query: str, params: dict) -> int:
    result = db.execute(text(query), params)
    db.commit()
    return result.lastrowid
