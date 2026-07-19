import json
import sqlite3

from fastapi.testclient import TestClient

from app.api.v2 import auth_router
from app.main import app


def test_login_issues_token_and_context_resolves_role():
    client = TestClient(app)
    response = client.post("/api/v2/auth/login", json={"employee_id": "MGR-HN-01", "password": "demo1234"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    context = client.get("/api/v2/me/context", headers={"Authorization": f"Bearer {token}"})
    assert context.status_code == 200
    assert context.json()["authorization_context"]["roles"] == ["manager"]


def test_login_rejects_bad_password():
    response = TestClient(app).post("/api/v2/auth/login", json={"employee_id": "RM-999", "password": "wrong"})
    assert response.status_code == 401


def test_tampered_session_token_is_rejected():
    client = TestClient(app)
    token = client.post("/api/v2/auth/login", json={"employee_id": "RM-999", "password": "demo1234"}).json()["access_token"]
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    response = client.get("/api/v2/me/context", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401


def test_customer_can_self_register_demo_profile(tmp_path, monkeypatch):
    db_path = tmp_path / "enterprise.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE customers (customer_id TEXT PRIMARY KEY, profile_version TEXT, attributes JSON);
            CREATE TABLE employees (employee_id TEXT PRIMARY KEY, role TEXT, organization_unit TEXT);
            CREATE TABLE permissions (employee_id TEXT PRIMARY KEY, permissions JSON, access_scope JSON);
            """
        )
    monkeypatch.setattr(auth_router, "_enterprise_sqlite_path", lambda: db_path)
    monkeypatch.setattr(auth_router.settings, "DATABASE_URL", "")
    monkeypatch.setattr(auth_router.settings, "DEMO_AUTH_ENABLED", True)

    client = TestClient(app)
    payload = {
        "company_name": "Công ty Khách Hàng Mới",
        "tax_code": "0101234567",
        "industry": "Sản xuất",
        "contact_name": "Nguyễn An",
    }
    created = client.post("/api/v2/auth/customer-users", json=payload)
    assert created.status_code == 201

    body = created.json()
    users = client.get("/api/v2/auth/customer-users").json()
    assert users == [{
        "employee_id": body["employee_id"],
        "customer_id": body["customer_id"],
        "company_name": payload["company_name"],
    }]
    with sqlite3.connect(db_path) as conn:
        attributes = json.loads(conn.execute("SELECT attributes FROM customers").fetchone()[0])
        scope = json.loads(conn.execute("SELECT access_scope FROM permissions").fetchone()[0])
    assert attributes["registration_source"] == "CUSTOMER_SELF_SERVICE"
    assert scope["managed_customer_ids"] == [body["customer_id"]]

    duplicate = client.post("/api/v2/auth/customer-users", json=payload)
    assert duplicate.status_code == 409
