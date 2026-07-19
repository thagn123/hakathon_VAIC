"""Small deterministic migration registry for the V2 PostgreSQL state store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: Iterable[str]


MIGRATIONS = (
    Migration(
        version=1,
        name="baseline_v2_repository",
        statements=(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
        ),
    ),
    Migration(
        version=2,
        name="sales_case_document_intake",
        statements=(
            """CREATE TABLE IF NOT EXISTS intake_sessions (
                intake_id TEXT PRIMARY KEY,
                case_id TEXT UNIQUE NOT NULL,
                employee_id TEXT NOT NULL,
                customer_id TEXT,
                status TEXT NOT NULL,
                version INTEGER NOT NULL,
                state_json JSONB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_intake_employee_status ON intake_sessions(employee_id,status,updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_intake_customer ON intake_sessions(customer_id,updated_at)",
            """CREATE TABLE IF NOT EXISTS case_documents (
                document_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                document_json TEXT NOT NULL,
                sections_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(intake_id,sha256),
                FOREIGN KEY(intake_id) REFERENCES intake_sessions(intake_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_case_documents_intake_status ON case_documents(intake_id,status)",
            """CREATE TABLE IF NOT EXISTS document_processing_jobs (
                job_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 1,
                error_code TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(document_id,stage),
                FOREIGN KEY(intake_id) REFERENCES intake_sessions(intake_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_jobs_status_updated ON document_processing_jobs(status,updated_at)",
            """CREATE TABLE IF NOT EXISTS document_extractions (
                extraction_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                location TEXT NOT NULL,
                text_value TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES case_documents(document_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_extractions_document ON document_extractions(document_id)",
            """CREATE TABLE IF NOT EXISTS extracted_fields (
                field_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                source_document_id TEXT NOT NULL,
                confidence REAL NOT NULL,
                validation_status TEXT NOT NULL,
                field_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(intake_id) REFERENCES intake_sessions(intake_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_fields_intake_name ON extracted_fields(intake_id,field_name)",
            """CREATE TABLE IF NOT EXISTS field_conflicts (
                conflict_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                requires_confirmation INTEGER NOT NULL,
                conflict_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(intake_id) REFERENCES intake_sessions(intake_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_conflicts_intake_blocking ON field_conflicts(intake_id,requires_confirmation)",
            """CREATE TABLE IF NOT EXISTS customer_profile_drafts (
                snapshot_id TEXT PRIMARY KEY,
                intake_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot_hash TEXT NOT NULL,
                rm_confirmed INTEGER NOT NULL,
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(intake_id,revision),
                FOREIGN KEY(intake_id) REFERENCES intake_sessions(intake_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_profiles_intake_confirmed ON customer_profile_drafts(intake_id,rm_confirmed)",
        ),
    ),
)

LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version


def apply_migrations(connection: Any) -> int:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    applied = {
        int(row["version"])
        for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        for statement in migration.statements:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
            (migration.version, migration.name),
        )
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
    return int(row["v"])
