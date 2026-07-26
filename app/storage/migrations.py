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
            """CREATE TABLE IF NOT EXISTS companies (
                tax_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                established_date TEXT,
                legal_form TEXT,
                registered_address TEXT,
                business_address TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS corporate_credit_requests (
                request_id TEXT PRIMARY KEY,
                case_id TEXT,
                customer_id TEXT,
                submitted_by TEXT,
                company_name TEXT,
                tax_id TEXT,
                legal_type TEXT,
                representative TEXT,
                industry TEXT,
                business_scale TEXT,
                total_assets_billion_vnd REAL,
                net_revenue_billion_vnd REAL,
                net_profit_billion_vnd REAL,
                debt_to_equity_ratio REAL,
                cic_debt_classification TEXT,
                current_debt_billion_vnd REAL,
                collateral_description TEXT,
                collateral_value_billion_vnd REAL,
                casa_avg_balance_billion_vnd REAL,
                repayment_history TEXT,
                request_type TEXT,
                requested_amount_vnd REAL,
                requested_term_months INTEGER,
                purpose TEXT,
                status TEXT NOT NULL DEFAULT 'WithRM',
                assigned_rm_id TEXT,
                rm_note TEXT,
                forward_idempotency_key TEXT,
                forwarded_at TEXT,
                service_recommendation TEXT,
                service_recommendation_summary TEXT,
                service_recommended_at TEXT,
                assigned_expert_id TEXT,
                appraisal_status TEXT DEFAULT 'pending',
                appraisal_summary TEXT,
                appraisal_score REAL,
                agent_recommendation TEXT,
                specialist_recommendation TEXT,
                specialist_reason TEXT,
                appraisal_idempotency_key TEXT,
                final_decision TEXT,
                decision_reason TEXT,
                approved_by TEXT,
                submission_idempotency_key TEXT,
                decision_idempotency_key TEXT,
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                appraised_at TEXT,
                decided_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_credit_requests_customer ON corporate_credit_requests(customer_id, submitted_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_credit_requests_status ON corporate_credit_requests(status, submitted_at DESC)",
        ),
    ),
    Migration(
        version=3,
        name="p0_document_request_timeline_notifications",
        statements=(
            # RM "create proposal" is a distinct, gated, auditable step
            # between a Credit Specialist clearing an appraisal and a
            # Manager's final decision -- see credit_request_repository.py
            # decide()'s proposal_created_at guard.
            "ALTER TABLE corporate_credit_requests ADD COLUMN proposal_created_at TEXT",
            "ALTER TABLE corporate_credit_requests ADD COLUMN proposal_created_by TEXT",
            "ALTER TABLE corporate_credit_requests ADD COLUMN proposal_note TEXT",
            "ALTER TABLE corporate_credit_requests ADD COLUMN proposal_idempotency_key TEXT",
            """CREATE TABLE IF NOT EXISTS customer_document_requests (
                request_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                credit_request_id TEXT,
                customer_id TEXT NOT NULL,
                created_by_role TEXT NOT NULL,
                created_by_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                customer_safe_reason TEXT NOT NULL,
                internal_reason TEXT,
                status TEXT NOT NULL DEFAULT 'REQUESTED',
                current_document_id TEXT,
                replacement_document_id TEXT,
                created_at TEXT NOT NULL,
                submitted_at TEXT,
                resolved_at TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS idx_doc_requests_case ON customer_document_requests(case_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_doc_requests_customer_status ON customer_document_requests(customer_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_requests_credit_request ON customer_document_requests(credit_request_id)",
            # Append-only appraisal history for the Credit Request pipeline --
            # corporate_credit_requests.specialist_reason/specialist_recommendation
            # are flat columns that appraise() UPDATEs in place, so round 2
            # silently erases round 1. This table is the durable history;
            # the flat columns remain the "current/latest" read path used by
            # existing UI/endpoints.
            """CREATE TABLE IF NOT EXISTS credit_request_review_rounds (
                review_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                case_id TEXT,
                review_round INTEGER NOT NULL,
                specialist_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                specialist_reason TEXT,
                appraisal_summary TEXT,
                appraisal_score REAL,
                agent_recommendation TEXT,
                document_request_id TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(request_id, review_round)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_review_rounds_request ON credit_request_review_rounds(request_id, review_round)",
            """CREATE TABLE IF NOT EXISTS timeline_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                entity_type TEXT,
                entity_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_timeline_case ON timeline_events(case_id, created_at)",
            """CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                recipient_id TEXT NOT NULL,
                recipient_role TEXT NOT NULL,
                case_id TEXT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                route TEXT,
                read_at TEXT,
                created_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, read_at, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_case ON notifications(case_id)",
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
