"""PostgreSQL connection helpers for the V2 state store.

This module is the single place that knows about psycopg2. Everything else
(``repository.py``, ``employee_db.py``) keeps the SQLite-era ergonomics --
``connection.execute("... WHERE x=?", (x,)).fetchone()`` and dict-like rows --
so the migration is mostly a dialect change, not a rewrite of every method.

Two entry points:

* ``connect()``  -- context manager yielding a ``_Conn`` that exposes
  ``.execute()`` directly on the connection (SQLite style) and commits on a
  clean exit / rolls back on error. Used by ``repository.py``.
* ``raw_connection()`` -- a plain psycopg2 connection whose default cursor
  translates ``?`` placeholders to ``%s`` and returns dict rows. Used by
  ``employee_db.py``, which manages its own ``commit()``/``close()``.

``Json`` is re-exported so callers can wrap Python objects destined for JSONB
columns (psycopg2 needs ``Json(obj)`` rather than a bare ``str`` for JSONB).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

import psycopg2
from psycopg2.extras import Json, RealDictCursor  # noqa: F401  (Json re-exported)

from app.config import settings


def _dsn() -> str:
    dsn = settings.DATABASE_URL
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not configured; the PostgreSQL state store requires it. "
            "Set DATABASE_URL=postgresql://user:pass@host:5432/dbname"
        )
    return dsn


def _translate(query: str) -> str:
    """SQLite uses ``?`` placeholders; psycopg2 uses ``%s``.

    Safe here because none of our SQL contains a literal ``?`` or ``%`` -- the
    only ``?`` are bind placeholders. A literal ``%`` would need escaping to
    ``%%`` for psycopg2, but we have none.
    """
    return query.replace("?", "%s") if "?" in query else query


class _CompatCursor(RealDictCursor):
    """RealDictCursor (rows accessible by column name) that also accepts the
    SQLite ``?`` placeholder style so existing SQL strings work unchanged."""

    def execute(self, query: str, vars: Optional[Sequence[Any]] = None) -> Any:  # noqa: A002
        return super().execute(_translate(query), vars)

    def executemany(self, query: str, vars_list: Any) -> Any:  # noqa: A002
        return super().executemany(_translate(query), vars_list)


class _Conn:
    """Thin wrapper giving a psycopg2 connection a SQLite-like ``.execute()``.

    Each ``.execute()`` opens a fresh compat cursor and returns it, so callers
    can chain ``.fetchone()`` / ``.fetchall()`` / read ``.rowcount`` exactly as
    they did with sqlite3's ``Connection.execute``.
    """

    def __init__(self, raw: "psycopg2.extensions.connection") -> None:
        self._raw = raw

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _CompatCursor:
        cursor = self._raw.cursor(cursor_factory=_CompatCursor)
        cursor.execute(sql, params)
        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()


def raw_connection() -> "psycopg2.extensions.connection":
    """Plain psycopg2 connection with the compat cursor as default factory.

    Caller owns the lifecycle (``commit()`` / ``close()``), mirroring the old
    ``sqlite3.connect(...)`` usage in ``employee_db.py``.
    """
    return psycopg2.connect(_dsn(), connect_timeout=10, cursor_factory=_CompatCursor)


@contextmanager
def connect() -> Iterator[_Conn]:
    """Context-managed connection that commits on success, rolls back on error.

    Replaces ``with sqlite3.connect(...) as connection:`` -- SQLite committed on
    a clean ``with`` exit; we preserve that behaviour here.
    """
    raw = psycopg2.connect(_dsn(), connect_timeout=10)
    try:
        yield _Conn(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
