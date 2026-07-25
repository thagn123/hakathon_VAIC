"""PostgreSQL / SQLite connection helpers for the V2 state store.

Provides transparent database connectivity for both PostgreSQL (when DATABASE_URL is set)
and SQLite (when DATABASE_URL is empty, for zero-dependency local testing/demo).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

try:
    import psycopg2
    from psycopg2.extras import Json as PgJson, RealDictCursor
except ImportError:
    psycopg2 = None
    PgJson = None

from app.config import settings


def Json(obj: Any) -> Any:
    if settings.DATABASE_URL and psycopg2 is not None:
        return PgJson(obj)
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    return obj


def _translate(query: str) -> str:
    """SQLite uses ? placeholders; psycopg2 uses %s."""
    return query.replace("?", "%s") if "?" in query else query


class _SQLiteCompatCursor:
    """Cursor wrapper for sqlite3 to provide RealDictCursor ergonomics and
    Json column deserialization."""

    def __init__(self, raw_cursor: sqlite3.Cursor) -> None:
        self._cursor = raw_cursor

    def execute(self, query: str, vars: Optional[Sequence[Any]] = None) -> _SQLiteCompatCursor:
        translated = query.replace("%s", "?") if "%s" in query else query
        params = vars if vars is not None else ()

        if ";" in translated and not params:
            statements = [s.strip() for s in translated.split(";") if s.strip()]
            for s in statements:
                self._cursor.execute(s)
            return self

        clean_params = []
        for p in params:
            if isinstance(p, (dict, list)):
                clean_params.append(json.dumps(p, ensure_ascii=False))
            else:
                clean_params.append(p)

        self._cursor.execute(translated, tuple(clean_params))
        return self

    def executemany(self, query: str, vars_list: Any) -> _SQLiteCompatCursor:
        translated = query.replace("%s", "?") if "%s" in query else query
        clean_vars_list = []
        for params in vars_list:
            clean_params = [
                json.dumps(p, ensure_ascii=False) if isinstance(p, (dict, list)) else p
                for p in params
            ]
            clean_vars_list.append(tuple(clean_params))
        self._cursor.executemany(translated, clean_vars_list)
        return self

    def fetchone(self) -> Optional[dict[str, Any]]:
        row = self._cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class _SQLiteConn:
    def __init__(self, db_path: str) -> None:
        p = Path(db_path)
        if str(p) != ":memory:":
            p.parent.mkdir(parents=True, exist_ok=True)
        self._raw = sqlite3.connect(db_path)
        self._raw.row_factory = sqlite3.Row

    def cursor(self, *args: Any, **kwargs: Any) -> _SQLiteCompatCursor:
        return _SQLiteCompatCursor(self._raw.cursor())

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _SQLiteCompatCursor:
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


class _PgCompatCursor(RealDictCursor):
    def execute(self, query: str, vars: Optional[Sequence[Any]] = None) -> Any:  # noqa: A002
        return super().execute(_translate(query), vars)

    def executemany(self, query: str, vars_list: Any) -> Any:  # noqa: A002
        return super().executemany(_translate(query), vars_list)


class _PgConn:
    def __init__(self, raw: Any) -> None:
        self._raw = raw

    def cursor(self, *args: Any, **kwargs: Any) -> _PgCompatCursor:
        return self._raw.cursor(cursor_factory=_PgCompatCursor)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _PgCompatCursor:
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


def raw_connection(db_path: str | None = None) -> Any:
    dsn = settings.DATABASE_URL
    if dsn and psycopg2 is not None:
        return psycopg2.connect(dsn, connect_timeout=10, cursor_factory=_PgCompatCursor)
    return _SQLiteConn(db_path or settings.V2_DB_PATH)


@contextmanager
def connect(db_path: str | None = None) -> Iterator[Any]:
    dsn = settings.DATABASE_URL
    if dsn and psycopg2 is not None:
        raw = psycopg2.connect(dsn, connect_timeout=10)
        conn = _PgConn(raw)
    else:
        conn = _SQLiteConn(db_path or settings.V2_DB_PATH)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

