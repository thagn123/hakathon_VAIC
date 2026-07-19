"""Seed the PostgreSQL enterprise mirror (CRM / IAM / SSO) for pilot/demo.

The PostgreSQL enterprise adapters in ``app/integrations/pg.py`` read the
legacy-shaped tables ``customers`` / ``permissions`` / ``employees``. This
script copies the exact demo cast from the local SQLite mirror
(``data/mock_database/enterprise_core.sqlite3``) into PostgreSQL so that
Group B (CRM/IAM/SSO) behaves identically to local dev once ``DATABASE_URL``
is set.

Run once after configuring DATABASE_URL:

    python -m tools.seed_postgres_enterprise

Idempotent: uses ``CREATE TABLE IF NOT EXISTS`` + upsert, so re-running just
refreshes the rows.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from psycopg2.extras import Json

from app.storage import pg

SQLITE_MIRROR = Path("data/mock_database/enterprise_core.sqlite3")

_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    profile_version TEXT,
    attributes JSONB
);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    role TEXT,
    organization_unit TEXT
);
CREATE TABLE IF NOT EXISTS permissions (
    employee_id TEXT PRIMARY KEY,
    permissions JSONB,
    access_scope JSONB
);
"""


def _load_sqlite() -> tuple[list, list, list]:
    if not SQLITE_MIRROR.exists():
        raise SystemExit(
            f"SQLite mirror not found at {SQLITE_MIRROR}. "
            "Run scripts/init_enterprise_db.py first, or seed PostgreSQL from your own source."
        )
    conn = sqlite3.connect(SQLITE_MIRROR)
    conn.row_factory = sqlite3.Row
    customers = conn.execute("SELECT customer_id, profile_version, attributes FROM customers").fetchall()
    employees = conn.execute("SELECT employee_id, role, organization_unit FROM employees").fetchall()
    perms = conn.execute("SELECT employee_id, permissions, access_scope FROM permissions").fetchall()
    conn.close()
    return customers, employees, perms


def seed() -> None:
    customers, employees, perms = _load_sqlite()
    with pg.connect() as connection:
        connection.execute(_DDL)
        for row in customers:
            connection.execute(
                "INSERT INTO customers (customer_id, profile_version, attributes) VALUES (?, ?, ?) "
                "ON CONFLICT (customer_id) DO UPDATE SET "
                "profile_version = excluded.profile_version, attributes = excluded.attributes",
                (row["customer_id"], row["profile_version"], Json(json.loads(row["attributes"]))),
            )
        for row in employees:
            connection.execute(
                "INSERT INTO employees (employee_id, role, organization_unit) VALUES (?, ?, ?) "
                "ON CONFLICT (employee_id) DO UPDATE SET "
                "role = excluded.role, organization_unit = excluded.organization_unit",
                (row["employee_id"], row["role"], row["organization_unit"]),
            )
        for row in perms:
            connection.execute(
                "INSERT INTO permissions (employee_id, permissions, access_scope) VALUES (?, ?, ?) "
                "ON CONFLICT (employee_id) DO UPDATE SET "
                "permissions = excluded.permissions, access_scope = excluded.access_scope",
                (row["employee_id"], Json(json.loads(row["permissions"])), Json(json.loads(row["access_scope"]))),
            )
    print(f"Seeded PostgreSQL enterprise mirror: {len(customers)} customers, "
          f"{len(employees)} employees, {len(perms)} permissions.")


if __name__ == "__main__":
    seed()
