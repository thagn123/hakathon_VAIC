"""Demo lifecycle API: reset the application's ACTIVE database and reseed
exactly one clean credit-workflow demo case.

Previously this endpoint hardcoded a second SQLite file
(data/mock_database/enterprise_core.sqlite3) that holds SSO/IAM identity data
only (see app/integrations/enterprise.py) -- none of the case/credit-request/
workflow tables it tried to DELETE FROM (corporate_credit_requests,
intake_sessions, cases, documents) exist in that file, so every DELETE
silently hit sqlite3.OperationalError and was swallowed. The endpoint never
actually cleared any real data (see reports/17_CROSS_ROLE_REALITY_CHECK.md).
This version reuses app.storage.pg (the same connection resolver every other
endpoint in this app uses -- Postgres via settings.DATABASE_URL when set,
otherwise SQLite via settings.V2_DB_PATH) so it always targets the database
the running app is actually reading/writing.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter

from app.config import settings
from app.credit.service import CreditReadinessService
from app.schemas.v2.credit_request import CorporateCreditRequestCreate
from app.storage import pg
from app.storage.credit_request_repository import CreditRequestRepository
from app.storage.repository import V2Repository

router = APIRouter(prefix="/demo", tags=["demo"])

# Every table that can hold per-case/per-request demo data, in dependency-safe
# order (a table is only cleared after every table that references its rows
# has already been cleared) so a reset is safe to run against a live schema
# with foreign keys enabled. Deliberately excludes schema_migrations and the
# employee/persona/consent/habit tables (employee_personas,
# employee_preferences, employee_habits, employee_consent,
# employee_recommendation_feedback, operational_readiness) -- those hold IAM/
# personalization configuration, not per-case demo data, and clearing them
# would break login for the current process. Also excludes `companies`,
# which is dead schema (declared in migrations.py, never read or written by
# any endpoint -- confirmed by repo-wide search).
_DEMO_DATA_TABLES = (
    # 1. Notifications -- leaf records, nothing else references them.
    "notifications",
    # 2. Timeline events -- append-only case history, also leaf.
    "timeline_events",
    # 3. Next-Best-Work / specialist work items.
    "employee_work_items",
    # 4. Specialist review history (credit appraisal rounds + Product/Legal/
    # Insurance specialist_reviews).
    "credit_request_review_rounds",
    "specialist_reviews",
    # 5. Customer document requests (resubmission workflow).
    "customer_document_requests",
    # 6. Approvals (SalesCase proposal-preview/approve/execute-actions branch).
    "approval_tokens",
    # 7. Evidence / document links extracted from uploaded files.
    "document_extractions",
    "extracted_fields",
    "field_conflicts",
    "document_processing_jobs",
    # 8. Documents themselves.
    "case_documents",
    # 9. Credit requests.
    "corporate_credit_requests",
    # 10. Sales cases and everything scoped to them.
    "intake_sessions",
    "customer_profile_drafts",
    "cases",
    "audit_events",
    "idempotency_records",
    "metadata_events",
    "metadata_relations",
    "metadata_versions",
    "metadata_objects",
)

# Matches the real Minh Phat customer persona already wired into
# app/integrations/enterprise.py's demo IAM personas (USER-MP-001 /
# COMP-MP), so the seeded case is immediately visible/actionable by the
# existing demo Customer/RM/Credit Specialist/Manager logins.
_DEMO_CUSTOMER_ID = "COMP-MP"
_DEMO_SUBMITTED_BY = "USER-MP-001"


def _seed_clean_credit_case() -> Dict[str, Any]:
    """Creates exactly one fresh credit-workflow demo case through the same
    repository/service path the real customer-facing endpoint uses
    (app/api/v2/credit_request_router.py:create_credit_request) -- not a
    hand-written INSERT -- so the seeded row is indistinguishable from one a
    real customer submitted and is immediately usable through the normal
    RM forward -> Credit Specialist appraise -> RM proposal -> Manager
    decision journey."""
    body = CorporateCreditRequestCreate(
        customer_id=_DEMO_CUSTOMER_ID,
        company_name="Cong ty TNHH Minh Phat",
        tax_id="0109876543",
        legal_type="LLC",
        representative="Nguyen Van Phat",
        industry="San xuat va thuong mai",
        business_scale="Vua va nho",
        total_assets_billion_vnd=Decimal("120.0"),
        net_revenue_billion_vnd=Decimal("85.0"),
        net_profit_billion_vnd=Decimal("9.5"),
        debt_to_equity_ratio=Decimal("0.8"),
        cic_debt_classification="Nhom 1 (No du tieu chuan)",
        current_debt_billion_vnd=Decimal("12.0"),
        collateral_description="Bat dong san tru so chinh va nha xuong san xuat",
        collateral_value_billion_vnd=Decimal("40.0"),
        casa_avg_balance_billion_vnd=Decimal("6.0"),
        repayment_history="Hoan hao",
        request_type="loan",
        requested_amount_vnd=Decimal("20000000000"),
        requested_term_months=36,
        purpose="Bo sung von luu dong phuc vu san xuat kinh doanh quy tiep theo.",
    )
    service_advisory = CreditReadinessService().recommend_services(body)
    row = CreditRequestRepository().create(
        body,
        submitted_by=_DEMO_SUBMITTED_BY,
        idempotency_key=f"demo-seed-{uuid.uuid4().hex}",
        service_advisory=service_advisory,
    )
    return {"request_id": row["request_id"], "case_id": row["case_id"], "status": row["status"]}


@router.post("/reset")
def reset_demo() -> Dict[str, Any]:
    """Resets the application's active database and reseeds exactly one
    clean credit-workflow demo case. Idempotent: safe to call any number of
    times in a row -- each call clears every synthetic table down to empty
    and leaves exactly one fresh credit request + implied sales case behind."""
    # V2Repository's constructor creates every table it and apply_migrations()
    # own (cases, audit_events, approval_tokens, idempotency_records,
    # metadata_*, plus the versioned migrations) if they don't already exist,
    # so this is safe to call even against a brand-new, empty database file --
    # it never assumes some other endpoint has already run first.
    V2Repository(settings.V2_DB_PATH)

    tables_cleared: List[str] = []
    with pg.connect() as connection:
        for table in _DEMO_DATA_TABLES:
            connection.execute(f"DELETE FROM {table}")
            tables_cleared.append(table)

    seeded_case = _seed_clean_credit_case()
    return {
        "status": "ok",
        "message": "Demo data reset successfully",
        "tables_cleared": tables_cleared,
        "seeded_case": seeded_case,
    }


@router.post("/seed")
def seed_demo() -> Dict[str, Any]:
    """Kept for backward compatibility with existing callers -- reset_demo()
    now does the reset-and-seed in one step, so this is just an alias."""
    return reset_demo()
