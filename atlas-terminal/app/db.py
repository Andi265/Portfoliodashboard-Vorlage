"""Datenbank-Cache. Jeder Datensatz wird unter einem Schlüssel (z. B. "history:AAPL")
als JSON gespeichert, zusammen mit Quelle, Zeitstempel und letztem Fehler.

Schlägt ein Abruf fehl, bleiben die letzten echten Daten erhalten und der Fehler wird
gespeichert. Gab es nie erfolgreiche Daten, liefert die API "Daten nicht verfügbar".
"""
import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(_url, pool_pre_ping=True, future=True)
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()


class CacheEntry(Base):
    __tablename__ = "cache"
    key = Column(String(100), primary_key=True)
    source = Column(String(200), nullable=False)
    data = Column(Text, nullable=True)            # JSON der letzten erfolgreichen Daten
    updated_at = Column(DateTime(timezone=True))  # Zeitpunkt der letzten erfolgreichen Daten
    attempted_at = Column(DateTime(timezone=True))
    error = Column(Text, nullable=True)           # Fehler des letzten Versuchs (None = ok)


def init_db():
    Base.metadata.create_all(engine)


def now_utc():
    return datetime.now(timezone.utc)


def store_ok(key: str, source: str, data):
    with Session() as s:
        row = s.get(CacheEntry, key) or CacheEntry(key=key, source=source)
        row.source = source
        row.data = json.dumps(data, default=str)
        row.updated_at = row.attempted_at = now_utc()
        row.error = None
        s.merge(row)
        s.commit()


def store_error(key: str, source: str, error: str):
    with Session() as s:
        row = s.get(CacheEntry, key) or CacheEntry(key=key, source=source)
        row.source = source
        row.attempted_at = now_utc()
        row.error = error[:2000]
        s.merge(row)
        s.commit()


def delete_prefix_except(prefix: str, keep: set):
    """Entfernt veraltete Einträge, z. B. FRED-Reihen, die es nicht mehr gibt."""
    with Session() as s:
        for row in s.execute(select(CacheEntry).where(CacheEntry.key.like(f"{prefix}%"))).scalars().all():
            if row.key not in keep:
                s.delete(row)
        s.commit()


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite verliert die Zeitzone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def load(key: str) -> dict:
    """Gibt {available, data, source, updated_at, error} zurück."""
    with Session() as s:
        row = s.get(CacheEntry, key)
        if row is None:
            return {"available": False, "data": None, "source": None, "updated_at": None,
                    "error": "Noch kein Abruf erfolgt"}
        return {
            "available": row.data is not None,
            "data": json.loads(row.data) if row.data else None,
            "source": row.source,
            "updated_at": _iso(row.updated_at),
            "attempted_at": _iso(row.attempted_at),
            "error": row.error,
        }


def status_all():
    with Session() as s:
        rows = s.execute(select(CacheEntry).order_by(CacheEntry.key)).scalars().all()
        return [{"key": r.key, "source": r.source, "updated_at": _iso(r.updated_at),
                 "attempted_at": _iso(r.attempted_at), "error": r.error,
                 "available": r.data is not None} for r in rows]
