"""Local login endpoint for the dashboard demo."""

from __future__ import annotations

import json
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
        db_path = Path(__file__).resolve().parents[3] / "data" / "mock_database" / "enterprise_core.sqlite3"
        conn = sqlite3.connect(db_path)
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
            names = {}
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
