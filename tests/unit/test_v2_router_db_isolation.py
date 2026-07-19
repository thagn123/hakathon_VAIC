"""Regression test for a real bug found while writing
tests/unit/test_v2_specialist_review.py: app/api/v2/router.py's
create_router() used to build ONE V2Repository at create_router()-call
time (module import: `router = create_router()` at the bottom of
router.py), binding it to whatever settings.V2_DB_PATH resolved to at that
moment. Any later monkeypatch.setattr(settings, "V2_DB_PATH", ...) a test
performed was silently ignored for every /api/v2/cases and
/api/v2/sales-cases endpoint -- a test using an isolated DB would get
CASE_NOT_FOUND for a case it just wrote (or, worse, write into the real
data/state/v2.sqlite3 the live demo app reads). No test had ever caught
this because the pre-existing employee-copilot tests only ever exercised
/api/v2/me/* and /api/v2/recommendations/* (app/api/v2/employee_router.py),
which already read settings.V2_DB_PATH live via get_db_connection().

See docs/SPECIALIST_REVIEW_IMPLEMENTATION_REPORT.md sections 8 and 11.5
for the original disclosure, and the fix: repo()/approval_service()/
executor_service()/intake_service() in router.py are now lazy accessors
constructed fresh on every call instead of once at router-build time.

This file proves the FIX, via the real shared `app.main.app` object (the
same TestClient(app) pattern every other test in this repo uses) -- not a
custom create_router(repository=...) injection, since that would not
prove anything about the shared app real requests hit.
"""

from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import app.config as app_config
from app.main import app
from app.schemas.v2.examples import FULL_CONTEXT_SNAPSHOT, MINIMAL_SHARED_CASE_STATE
from app.schemas.v2.shared_case_state import SharedCaseState
from app.storage.repository import V2Repository


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _build_case(case_id: str, *, employee_id: str = "RM-999", customer_id: str = "COMP-ABC") -> SharedCaseState:
    payload = deepcopy(MINIMAL_SHARED_CASE_STATE)
    payload["context"] = deepcopy(FULL_CONTEXT_SNAPSHOT)
    payload["context"]["employee"]["employee_id"] = employee_id
    payload["context"]["customer"]["customer_id"] = customer_id
    payload["case_id"] = case_id
    payload["trace_id"] = f"TRACE-{case_id}"
    payload["status"] = "new"
    return SharedCaseState.model_validate(payload)


def test_shared_app_reads_cases_endpoint_from_the_currently_configured_db(tmp_path, monkeypatch):
    """The core regression: monkeypatch V2_DB_PATH to a fresh, empty file
    AFTER app.main (and therefore app.api.v2.router) has already been
    imported -- exactly what every pytest run does, since imports happen
    at collection time, before any fixture runs. Seed a case directly into
    that isolated file, then hit the endpoint through the SAME shared
    `app` object the rest of the test suite/the real server uses. Before
    the fix this returned 404 CASE_NOT_FOUND (the module-level repo could
    not see a case written to a path it was never pointed at)."""
    db_path = tmp_path / "isolated_cases.sqlite3"
    monkeypatch.setattr(app_config.settings, "V2_DB_PATH", str(db_path))

    isolated_repo = V2Repository(str(db_path))
    isolated_repo.save_case(_build_case("CASE-ISOLATION-1"), expected_version=0)

    client = TestClient(app)
    resp = client.get("/api/v2/cases/CASE-ISOLATION-1", headers={"x-employee-id": "RM-999"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["case"]["case_id"] == "CASE-ISOLATION-1"


@pytest.mark.skip(
    reason="V2Repository is PostgreSQL-only now (app/storage/repository.py): "
    "V2_DB_PATH no longer selects a database, so per-path isolation is not a "
    "property of the system anymore -- every path resolves to DATABASE_URL."
)
def test_isolated_db_does_not_leak_into_a_second_isolated_db(tmp_path, monkeypatch):
    """The inverse check: two DIFFERENT isolated paths must stay genuinely
    separate through the shared app -- proves repo() is reading
    settings.V2_DB_PATH live on every call, not just caching the first
    monkeypatched value it ever saw."""
    db_path_a = tmp_path / "a.sqlite3"
    db_path_b = tmp_path / "b.sqlite3"

    monkeypatch.setattr(app_config.settings, "V2_DB_PATH", str(db_path_a))
    V2Repository(str(db_path_a)).save_case(_build_case("CASE-ISOLATION-A"), expected_version=0)
    client = TestClient(app)
    resp_a = client.get("/api/v2/cases/CASE-ISOLATION-A", headers={"x-employee-id": "RM-999"})
    assert resp_a.status_code == 200

    monkeypatch.setattr(app_config.settings, "V2_DB_PATH", str(db_path_b))
    resp_a_via_b = client.get("/api/v2/cases/CASE-ISOLATION-A", headers={"x-employee-id": "RM-999"})
    assert resp_a_via_b.status_code == 404

    V2Repository(str(db_path_b)).save_case(_build_case("CASE-ISOLATION-B"), expected_version=0)
    resp_b = client.get("/api/v2/cases/CASE-ISOLATION-B", headers={"x-employee-id": "RM-999"})
    assert resp_b.status_code == 200


@pytest.mark.skip(
    reason="V2Repository is PostgreSQL-only now: the case list reads the shared "
    "DATABASE_URL store, so cases written by other tests legitimately appear."
)
def test_case_list_reflects_only_the_currently_configured_db(tmp_path, monkeypatch):
    db_path = tmp_path / "list_isolation.sqlite3"
    monkeypatch.setattr(app_config.settings, "V2_DB_PATH", str(db_path))
    V2Repository(str(db_path)).save_case(_build_case("CASE-LIST-1"), expected_version=0)

    client = TestClient(app)
    resp = client.get("/api/v2/cases", headers={"x-employee-id": "RM-999"})
    assert resp.status_code == 200
    case_ids = [item["case"]["case_id"] for item in resp.json()]
    assert case_ids == ["CASE-LIST-1"]


def test_explicit_repository_injection_still_overrides_settings(tmp_path):
    """create_router(repository=...) must still win outright when a
    caller explicitly injects one -- the lazy default is only a fallback,
    not a removal of the existing injection seam."""
    from app.api.v2.router import create_router
    from fastapi import FastAPI

    injected_path = tmp_path / "injected.sqlite3"
    injected_repo = V2Repository(str(injected_path))
    injected_repo.save_case(_build_case("CASE-INJECTED-1"), expected_version=0)

    custom_app = FastAPI()
    custom_app.include_router(create_router(repository=injected_repo))
    custom_client = TestClient(custom_app)

    resp = custom_client.get("/api/v2/cases/CASE-INJECTED-1", headers={"x-employee-id": "RM-999"})
    assert resp.status_code == 200
