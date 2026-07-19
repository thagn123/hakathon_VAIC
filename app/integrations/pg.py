"""PostgreSQL-backed Enterprise adapters (CRM / IAM / SSO).

Drop-in replacements for the SQLite adapters in `enterprise.py`. They implement
the same ``CRMPort`` / ``IAMPort`` / ``SSOPort`` protocols so the FastAPI
router can switch between SQLite (local dev) and PostgreSQL (pilot/production)
via the ``DATABASE_URL`` setting.

The CRM/IAM/SSO mirror tables (``customers``, ``permissions``, ``employees``)
use the SAME columns the SQLite adapters expect, so the rest of the app is
untouched. The richer KYC schema (``companies``, ``financial_health`` …) lives
alongside these and is the long-term source of truth; this adapter keeps the
app working today by exposing the pilot demo cast (COMP-MP + the six personas)
through the legacy shape.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, TypedDict

try:  # pragma: no cover - import guard
    import psycopg2
    import psycopg2.extensions
    import psycopg2.pool
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

from app.integrations.errors import UpstreamTimeoutError, UpstreamUnavailableError


class CustomerProfile(TypedDict):
    customer_id: str
    profile_version: str
    attributes: Dict[str, Any]
    observed_at: str


class CRMPort(Protocol):
    def get_customer_profile(self, customer_id: str, *, correlation_id: str) -> CustomerProfile: ...


class PermissionGrant(TypedDict):
    permissions: List[str]
    access_scope: Dict[str, Any]


class IAMPort(Protocol):
    def get_permissions(self, employee_id: str, *, correlation_id: str) -> PermissionGrant: ...


class EmployeeIdentity(TypedDict):
    employee_id: str
    role: str
    organization_unit: str


class SSOPort(Protocol):
    def get_employee_identity(self, employee_id: str, *, correlation_id: str) -> EmployeeIdentity: ...


class EnterprisePostgresBase:
    """Thin psycopg2 wrapper. One connection per call (cheap, IPv6-safe)."""

    def __init__(self, database_url: str | None = None, *, fail_for: set[str] | None = None) -> None:
        if psycopg2 is None:
            raise RuntimeError(
                "psycopg2 is required for the PostgreSQL enterprise adapters. "
                "Install it with `pip install psycopg2-binary`."
            )
        from app.config import settings

        self.database_url = database_url or settings.DATABASE_URL
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured; cannot use PostgreSQL adapters.")
        self._fail_for = fail_for or set()

    def _connect(self):  # type: ignore[no-untyped-def]
        return psycopg2.connect(self.database_url, connect_timeout=5)


def _json_loads(value: Any) -> Any:
    """psycopg2 decodes JSONB columns to Python objects already; SQLite
    stored them as JSON text. Accept both so the adapter is backend-agnostic."""
    if isinstance(value, (str, bytes, bytearray)):
        return json.loads(value)
    return value


class PostgresCRMAdapter(EnterprisePostgresBase):
    def get_customer_profile(self, customer_id: str, *, correlation_id: str) -> CustomerProfile:
        if customer_id in self._fail_for:
            raise UpstreamTimeoutError(correlation_id, upstream="crm")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT profile_version, attributes FROM customers WHERE customer_id = %s",
                    (customer_id,),
                )
                row = cur.fetchone()

        if not row:
            raise UpstreamUnavailableError(
                correlation_id, upstream="crm", reason=f"unknown customer_id {customer_id}"
            )

        return {
            "customer_id": customer_id,
            "profile_version": row[0],
            "attributes": _json_loads(row[1]),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


class PostgresIAMAdapter(EnterprisePostgresBase):
    def get_permissions(self, employee_id: str, *, correlation_id: str) -> PermissionGrant:
        if employee_id in self._fail_for:
            raise UpstreamTimeoutError(correlation_id, upstream="iam")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT permissions, access_scope FROM permissions WHERE employee_id = %s",
                    (employee_id,),
                )
                row = cur.fetchone()

        if not row:
            return {"permissions": [], "access_scope": {"managed_customer_ids": [], "branch": None}}

        return {
            "permissions": _json_loads(row[0]),
            "access_scope": _json_loads(row[1]),
        }


class PostgresSSOAdapter(EnterprisePostgresBase):
    def get_employee_identity(self, employee_id: str, *, correlation_id: str) -> EmployeeIdentity:
        if employee_id in self._fail_for:
            raise UpstreamTimeoutError(correlation_id, upstream="sso")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT role, organization_unit FROM employees WHERE employee_id = %s",
                    (employee_id,),
                )
                row = cur.fetchone()

        if not row:
            raise UpstreamUnavailableError(
                correlation_id, upstream="sso", reason=f"unknown employee_id {employee_id}"
            )

        return {
            "employee_id": employee_id,
            "role": row[0],
            "organization_unit": row[1],
        }


# Imported by the KYC schema seeder so the demo cast is identical to the
# SQLite mirror (see tools/seed_postgres_enterprise.py).
EMPLOYEE_COPILOT_DEMO_PERSONAS: List[tuple[str, str, str, List[str], Dict[str, Any]]] = [
    ("USER-MP-001", "Customer", "Minh Phat Customer Portal",
     ["case:create", "case:read", "case:write"],
     {"managed_customer_ids": ["COMP-MP"], "branch": "CUSTOMER_PORTAL"}),
    ("USER-ABC-001", "Customer", "ABC Viet Nam Customer Portal",
     ["case:create", "case:read", "case:write"],
     {"managed_customer_ids": ["COMP-ABC"], "branch": "CUSTOMER_PORTAL"}),
    ("USER-XYZ-001", "Customer", "XYZ Customer Portal",
     ["case:create", "case:read", "case:write"],
     {"managed_customer_ids": ["COMP-XYZ"], "branch": "CUSTOMER_PORTAL"}),
    # Merged bank-staff persona: RM re-creates the file and appraises it;
    # Manager alone keeps credit:final_approve.
    ("RM-999", "RM", "Corporate Banking HN",
     ["case:read", "case:write", "approval:request", "credit:forward", "credit:appraise"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
    ("SPEC-LEGAL-001", "Specialist", "Legal & Compliance",
     ["case:read", "case:verify_evidence", "legal:check_issue", "legal:block_non_eligible",
      "legal:manage_knowledge"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
    ("SPEC-PROD-001", "Specialist", "Product",
     ["case:read", "product:recommend", "product:verify_fit", "product:manage_knowledge"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
    ("SPEC-CREDIT-001", "Specialist", "Credit Risk & Underwriting",
     ["case:read", "credit:analyze_file", "credit:review_structure",
      "credit:appraise", "credit:manage_knowledge"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
    ("SPEC-INSURANCE-001", "Specialist", "Corporate Insurance Advisory",
     ["case:read", "insurance:analyze_coverage", "insurance:review_coverage",
      "insurance:manage_knowledge"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
    ("MGR-HN-01", "Manager", "Branch HN Management",
     ["team:view_workload", "case:read", "credit:final_approve"],
     {"managed_customer_ids": ["COMP-ABC", "COMP-MP", "COMP-XYZ"], "branch": "HN01"}),
]
