"""Local login endpoint for the dashboard demo."""

from __future__ import annotations

import json
import hashlib
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import issue_session_token
from app.config import settings
from app.integrations.enterprise import SQLiteSSOAdapter
from app.integrations.pg import PostgresSSOAdapter
from app.integrations.errors import ContextError


def _sso_adapter():
    return PostgresSSOAdapter() if settings.DATABASE_URL else SQLiteSSOAdapter()


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    employee_id: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    employee_id: str


class CustomerRegistrationRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=300)
    tax_code: str = Field(min_length=3, max_length=30)
    industry: str = Field(default="", max_length=300)
    contact_name: str = Field(default="", max_length=200)


class CustomerRegistrationResponse(BaseModel):
    employee_id: str
    customer_id: str
    company_name: str


def _enterprise_sqlite_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "mock_database" / "enterprise_core.sqlite3"


def _registration_ids(tax_code: str) -> tuple[str, str]:
    normalized = "".join(char for char in tax_code.upper() if char.isalnum())
    suffix = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10].upper()
    return f"COMP-{suffix}", f"USER-{suffix}-001"


def _registration_payload(body: CustomerRegistrationRequest) -> tuple[str, str, Dict[str, Any]]:
    company_name = body.company_name.strip()
    tax_code = body.tax_code.strip()
    if len(company_name) < 2 or len("".join(char for char in tax_code if char.isalnum())) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CUSTOMER_PROFILE", "message": "Tên doanh nghiệp hoặc mã số thuế không hợp lệ."},
        )
    customer_id, employee_id = _registration_ids(tax_code)
    attributes = {
        "company_name": company_name,
        "tax_code": tax_code,
        "industry": body.industry.strip(),
        "contact": body.contact_name.strip(),
        "registration_source": "CUSTOMER_SELF_SERVICE",
    }
    return customer_id, employee_id, attributes


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, x_session_id: Optional[str] = Header(None)) -> LoginResponse:
    # Demo password is deliberately configured outside source control. In a
    # real deployment this endpoint must be replaced by the enterprise SSO.
    if not settings.DEMO_AUTH_ENABLED or body.password != settings.DEMO_LOGIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Sai tai khoan hoac mat khau."})
    try:
        identity = _sso_adapter().get_employee_identity(body.employee_id.upper(), correlation_id=f"TRACE-{uuid.uuid4().hex.upper()}")
    except ContextError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Sai tai khoan hoac mat khau."})
    token_ttl = settings.AUTH_TOKEN_TTL_SECONDS
    return LoginResponse(
        access_token=issue_session_token(identity["employee_id"], ttl_seconds=token_ttl),
        expires_in=token_ttl,
        employee_id=identity["employee_id"],
    )


@router.post("/customer-users", response_model=CustomerRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_customer_user(body: CustomerRegistrationRequest) -> CustomerRegistrationResponse:
    """Create a self-service Customer identity for the local/sandbox demo."""
    if not settings.DEMO_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SELF_REGISTRATION_DISABLED", "message": "Tự đăng ký chỉ được bật trong môi trường demo."},
        )

    customer_id, employee_id, attributes = _registration_payload(body)
    permissions = ["case:create", "case:read", "case:write"]
    access_scope = {"managed_customer_ids": [customer_id], "branch": "CUSTOMER_PORTAL"}

    if settings.DATABASE_URL:
        adapter = PostgresSSOAdapter()
        with adapter._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM customers WHERE customer_id = %s", (customer_id,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={"code": "CUSTOMER_ALREADY_EXISTS", "message": "Mã số thuế này đã có hồ sơ đăng nhập."},
                    )
                cur.execute(
                    "INSERT INTO companies (tax_id, company_name) VALUES (%s, %s) ON CONFLICT (tax_id) DO NOTHING",
                    (customer_id, attributes["company_name"]),
                )
                cur.execute(
                    "INSERT INTO customers (customer_id, profile_version, attributes) VALUES (%s, %s, %s)",
                    (customer_id, "self-registered-v1", json.dumps(attributes)),
                )
                cur.execute(
                    "INSERT INTO employees (employee_id, role, organization_unit) VALUES (%s, %s, %s)",
                    (employee_id, "Customer", f"{attributes['company_name']} Customer Portal"),
                )
                cur.execute(
                    "INSERT INTO permissions (employee_id, permissions, access_scope) VALUES (%s, %s, %s)",
                    (employee_id, json.dumps(permissions), json.dumps(access_scope)),
                )
    else:
        with sqlite3.connect(_enterprise_sqlite_path()) as conn:
            if conn.execute("SELECT 1 FROM customers WHERE customer_id = ?", (customer_id,)).fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "CUSTOMER_ALREADY_EXISTS", "message": "Mã số thuế này đã có hồ sơ đăng nhập."},
                )
            conn.execute(
                "INSERT INTO customers (customer_id, profile_version, attributes) VALUES (?, ?, ?)",
                (customer_id, "self-registered-v1", json.dumps(attributes, ensure_ascii=False)),
            )
            conn.execute(
                "INSERT INTO employees (employee_id, role, organization_unit) VALUES (?, ?, ?)",
                (employee_id, "Customer", f"{attributes['company_name']} Customer Portal"),
            )
            conn.execute(
                "INSERT INTO permissions (employee_id, permissions, access_scope) VALUES (?, ?, ?)",
                (employee_id, json.dumps(permissions), json.dumps(access_scope)),
            )

    return CustomerRegistrationResponse(
        employee_id=employee_id,
        customer_id=customer_id,
        company_name=attributes["company_name"],
    )


@router.get("/companies", response_model=List[Dict[str, Any]])
def list_companies() -> List[Dict[str, Any]]:
    """Public list for the workspace customer switcher: one row per company
    in `companies`. Only IDs and display names are exposed."""
    if settings.DATABASE_URL:
        adapter = PostgresSSOAdapter()
        with adapter._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tax_id, company_name FROM companies ORDER BY company_name")
                rows = cur.fetchall()
        return [{"customer_id": tax_id, "company_name": name} for tax_id, name in rows]
    # SQLite dev mirror has no `companies` table; the UI keeps its static
    # fallback options when this list is empty.
    return []


@router.get("/customer-users", response_model=List[Dict[str, Any]])
def list_customer_users() -> List[Dict[str, Any]]:
    """Public list for the login screen: customer-portal accounts and the
    company (from `companies`) each one belongs to. Exposes only IDs and
    company names — no permissions, no internal data."""
    if settings.DATABASE_URL:
        adapter = PostgresSSOAdapter()
        with adapter._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT e.employee_id, p.access_scope
                    FROM employees e JOIN permissions p USING (employee_id)
                    WHERE lower(e.role) IN ('customer', 'customer_user')
                    ORDER BY e.employee_id
                    """
                )
                rows = cur.fetchall()
                cur.execute("SELECT tax_id, company_name FROM companies")
                names = dict(cur.fetchall())
    else:
        conn = sqlite3.connect(_enterprise_sqlite_path())
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT e.employee_id, p.access_scope
                FROM employees e JOIN permissions p ON p.employee_id = e.employee_id
                WHERE lower(e.role) IN ('customer', 'customer_user')
                ORDER BY e.employee_id
                """
            )
            rows = cur.fetchall()
            cur.execute("SELECT customer_id, attributes FROM customers")
            names = {}
            for customer_id, raw_attributes in cur.fetchall():
                attributes = raw_attributes if isinstance(raw_attributes, dict) else json.loads(raw_attributes)
                names[customer_id] = attributes.get("company_name") or customer_id
        finally:
            conn.close()

    result: List[Dict[str, Any]] = []
    for employee_id, access_scope in rows:
        scope = access_scope if isinstance(access_scope, dict) else json.loads(access_scope)
        customer_ids = scope.get("managed_customer_ids") or []
        customer_id = customer_ids[0] if customer_ids else None
        result.append({
            "employee_id": employee_id,
            "customer_id": customer_id,
            "company_name": names.get(customer_id, customer_id or employee_id),
        })
    return result
