"""Persistence, concurrency, audit and approval safety tests."""

from __future__ import annotations

import pytest

from app.approval.service import ApprovalError, ApprovalServiceV2
from app.schemas.v2.examples import MINIMAL_SHARED_CASE_STATE
from app.schemas.v2.shared_case_state import SharedCaseState
from app.storage.migrations import LATEST_SCHEMA_VERSION
from app.storage.repository import StateConflictError, V2Repository


def state():
    return SharedCaseState.model_validate(MINIMAL_SHARED_CASE_STATE)


def test_case_survives_repository_restart_and_uses_optimistic_locking(tmp_path):
    path = tmp_path / "state.sqlite3"
    first = V2Repository(path)
    stored = first.save_case(state())
    restarted = V2Repository(path)
    assert restarted.get_case("CASE-001").state.case_id == "CASE-001"
    restarted.save_case(stored.state, expected_version=1)
    with pytest.raises(StateConflictError):
        restarted.save_case(stored.state, expected_version=1)


def test_audit_chain_is_verifiable_and_redacts_tokens(tmp_path):
    repository = V2Repository(tmp_path / "state.sqlite3")
    repository.append_audit(
        event_id="E1", case_id="CASE-001", trace_id="TRACE-001", actor="RM-1",
        action="approve", payload={"approval_token": "secret-token", "status": "ok"},
    )
    repository.append_audit(
        event_id="E2", case_id="CASE-001", trace_id="TRACE-001", actor="SYSTEM",
        action="execute", payload={"result": "ok"},
    )
    assert repository.verify_audit_chain("CASE-001")
    assert repository.audit_events("CASE-001")[0]["payload"]["approval_token"] == "[REDACTED]"


def test_approval_is_bound_to_payload_and_one_time_use(tmp_path):
    repository = V2Repository(tmp_path / "state.sqlite3")
    service = ApprovalServiceV2(repository, secret="unit-test-secret", ttl_seconds=60)
    payload = {"action": "create_crm_case", "case_id": "CASE-001", "subject": "Payroll"}
    issued = service.issue(
        case_id="CASE-001", approver_id="RM-999", permissions=["create_crm_case"], payload=payload
    )
    with pytest.raises(ApprovalError, match="payload changed"):
        service.verify_and_consume(
            issued["token"], case_id="CASE-001", approver_id="RM-999",
            payload={**payload, "subject": "Changed"}, permission="create_crm_case",
        )
    service.verify_and_consume(
        issued["token"], case_id="CASE-001", approver_id="RM-999",
        payload=payload, permission="create_crm_case",
    )
    with pytest.raises(ApprovalError, match="consumed"):
        service.verify_and_consume(
            issued["token"], case_id="CASE-001", approver_id="RM-999",
            payload=payload, permission="create_crm_case",
        )


def test_idempotency_returns_original_result(tmp_path):
    repository = V2Repository(tmp_path / "state.sqlite3")
    first = repository.save_idempotent_result("K1", "create", "sha256:a", {"external_id": "CRM-1"})
    replay = repository.save_idempotent_result("K1", "create", "sha256:b", {"external_id": "CRM-2"})
    assert first == replay == {"external_id": "CRM-1"}


def test_repository_migration_and_health_are_restart_safe(tmp_path):
    path = tmp_path / "state.sqlite3"
    repository = V2Repository(path)
    assert repository.schema_version() == LATEST_SCHEMA_VERSION == 3
    assert repository.health()["healthy"] is True
    restarted = V2Repository(path)
    assert restarted.schema_version() == LATEST_SCHEMA_VERSION
    assert restarted.health()["quick_check"] == "ok"
