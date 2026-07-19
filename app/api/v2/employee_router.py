"""API Router for Employee personalization, work context, consent and Next Best Work.

Identity flow (P0 fix, see docs/ROLE_AWARE_REPO_VERIFICATION_REPORT.md P0-1/P0-2):

    Authorization: Bearer <token>  (or, in DEMO_AUTH_ENABLED mode, X-Employee-ID)
    -> require_verified_identity()
    -> EmployeeContextService(SQLiteSSOAdapter, SQLiteIAMAdapter)   [the SAME
       ports app/api/v2/router.py already uses -- one IAM, not two]
    -> VerifiedIdentity (role/permissions/customer_scope from IAM, never from
       request body/query, never from the employee_db personalization store)

`employee_db` (data/state/v2.sqlite3) is now used ONLY for what it should
always have been: personalization preferences, consent, habits, work items
and recommendation feedback -- never identity, role or permission lookup.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.auth import verify_session_token
from app.context.employee_service import EmployeeContextService
from app.context.next_best_work import get_next_best_work
from app.integrations.enterprise import (
    SQLiteIAMAdapter,
    SQLiteSSOAdapter,
    ensure_employee_copilot_demo_personas,
    map_enterprise_role_to_role_type,
)
from app.integrations.pg import (
    PostgresIAMAdapter,
    PostgresSSOAdapter,
)


def _employee_iam_adapter(fail_for=None):
    return PostgresIAMAdapter(fail_for=fail_for) if settings.DATABASE_URL else SQLiteIAMAdapter(fail_for=fail_for)


def _employee_sso_adapter(fail_for=None):
    return PostgresSSOAdapter(fail_for=fail_for) if settings.DATABASE_URL else SQLiteSSOAdapter(fail_for=fail_for)


from app.integrations.errors import ContextError, UpstreamTimeoutError, UpstreamUnavailableError
from app.knowledge.legal_service import LegalKnowledgeService
from app.knowledge.credit_service import CreditKnowledgeService
from app.knowledge.insurance_service import InsuranceKnowledgeService
from app.knowledge.models import KnowledgeChunk
from app.knowledge.retrieval_contracts import AuthorityTier, VerificationStatus
from app.knowledge.service import ProductKnowledgeService
from app.observability.runtime import JsonEventLogger, metrics
from app.reliability.capability_registry import has_capability
from app.storage.repository import StateConflictError, V2Repository
from app.schemas.v2.agent_knowledge import (
    DOMAIN_BY_ROLE,
    MANAGE_CAPABILITY_BY_DOMAIN,
    AgentActivitySnapshot,
    AgentCaseActivityItem,
    AgentDomain,
    KnowledgeEntryCreateRequest,
    KnowledgeEntryRecord,
    KnowledgeEntryUpdateRequest,
    default_chunk_type,
)
from app.schemas.v2.employee import (
    AuthorizationContext,
    ConsentModel,
    EmployeeContextSnapshot,
    HabitModel,
    HabitStatus,
    PersonalizationContext,
    ProvenanceMetadata,
    ProvenanceType,
    RoleType,
    VerifiedIdentity,
    WorkContext,
)
from app.schemas.v2.planning import NextBestQuestion
from app.schemas.v2.shared_case_state import ApprovalStatus, CaseStatus
from app.schemas.v2.specialist_review import (
    OperationalReadinessRequest,
    OperationalReadinessSnapshot,
    SpecialistReviewRecord,
    SpecialistReviewRequest,
    SpecialistReviewResult,
)
from app.storage.employee_db import (
    cleared_roles_for_case_version,
    confirm_habit,
    create_work_item,
    delete_habit,
    get_consent,
    get_db_connection,
    get_habits,
    get_operational_readiness,
    get_preferences,
    init_employee_db,
    list_specialist_reviews,
    reject_habit,
    save_consent,
    save_operational_readiness,
    save_preferences,
    save_recommendation_feedback,
    save_specialist_review,
)
from app.workflow.engine import V2WorkflowEngine
from app.workflow.state_machine import transition

logger = logging.getLogger(__name__)
_event_logger = JsonEventLogger(settings.AUDIT_LOG_PATH)

# Schema/seed setup runs once at process start (mirrors V2Repository's
# create-table-if-not-exists-on-construct convention -- see
# app/storage/repository.py). Previously init_employee_db() was defined but
# never called anywhere, so a fresh checkout/CI run had no `employees` table
# at all; every /api/v2/me/* call would have raised sqlite3.OperationalError.
init_employee_db()
ensure_employee_copilot_demo_personas()
# get_my_context()/get_team_workload() read the `cases` table directly
# (read-only cross-module query); ensure it exists even if this module is
# the first thing to touch settings.V2_DB_PATH (e.g. a fresh isolated test
# DB, or the employee layer being hit before any sales-case flow has run).
V2Repository(settings.V2_DB_PATH)


def _repo() -> V2Repository:
    """Construct fresh on every call (never cache the instance at module
    scope) so it reads settings.V2_DB_PATH live -- mirrors
    app/storage/employee_db.py's get_db_connection(). A module-level
    singleton here would bind to whatever V2_DB_PATH was at import time,
    silently ignoring a test's monkeypatched isolated DB (the exact bug
    already found and fixed once for employee_db.py's old module-level
    DB_PATH constant -- see docs/ROLE_AWARE_P0_FIX_IMPLEMENTATION_REPORT.md)."""
    return V2Repository(settings.V2_DB_PATH)


router = APIRouter(prefix="/me", tags=["Employee Copilot"])
recommendation_router = APIRouter(prefix="/recommendations", tags=["Employee Copilot"])
case_action_router = APIRouter(prefix="/cases", tags=["Specialist Review"])
knowledge_router = APIRouter(prefix="/me/agent-knowledge", tags=["Agent Knowledge Console"])

_DEMO_TOKEN_PREFIX = "demo-"


class ErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool
    request_id: str


def _error(status_code: int, code: str, message: str, *, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "retryable": retryable,
                           "request_id": f"REQ-{uuid.uuid4().hex[:8].upper()}"}},
    )


def _resolve_demo_employee_id(raw: str) -> str:
    """"demo-rm-999" -> "RM-999", "demo-spec-legal-001" -> "SPEC-LEGAL-001"."""
    if raw.lower().startswith(_DEMO_TOKEN_PREFIX):
        return raw[len(_DEMO_TOKEN_PREFIX):].upper()
    return raw


def require_verified_identity(
    authorization: Optional[str] = Header(None),
    x_employee_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
) -> VerifiedIdentity:
    """The single place identity is resolved for every route in this file
    and in recommendation_router. Never trusts a role/employee_id from the
    request body or query string -- only from a header, and only ever used
    to look an identity up via SSOPort/IAMPort (it is never itself treated
    as authorization)."""
    correlation_id = f"TRACE-{uuid.uuid4().hex.upper()}"
    session_id = x_session_id or "SESS-DEFAULT"

    raw_credential: Optional[str] = None
    auth_source: str = "demo"

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        session_payload = verify_session_token(token)
        if session_payload is not None:
            raw_credential = str(session_payload["sub"])
            auth_source = "sso"
        elif token.startswith("shb."):
            _event_logger.emit("authentication_failed", reason="invalid_session_token", correlation_id=correlation_id)
            raise _error(status.HTTP_401_UNAUTHORIZED, "UNAUTHENTICATED", "Phien dang nhap khong hop le hoac da het han.")
        elif token == "EXPIRED_TOKEN":
            _event_logger.emit("authentication_failed", reason="token_expired", correlation_id=correlation_id)
            raise _error(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "Token phien dang nhap da het han.")
        elif token.lower().startswith(_DEMO_TOKEN_PREFIX):
            if not settings.DEMO_AUTH_ENABLED:
                _event_logger.emit("authentication_failed", reason="demo_auth_disabled", correlation_id=correlation_id)
                raise _error(status.HTTP_401_UNAUTHORIZED, "UNAUTHENTICATED", "Demo auth dang bi tat.")
            raw_credential = _resolve_demo_employee_id(token)
            auth_source = "demo"
        else:
            # No real external SSO exists in this synthetic MVP; a
            # non-demo bearer token is treated as an already-verified
            # session's employee_id and is STILL required to resolve
            # through SSOPort/IAMPort below -- an unrecognized value is
            # rejected there (403), not trusted blindly.
            raw_credential = token
            auth_source = "sso"
    elif x_employee_id:
        if not settings.DEMO_AUTH_ENABLED:
            _event_logger.emit("authentication_failed", reason="header_auth_disabled", correlation_id=correlation_id)
            raise _error(status.HTTP_401_UNAUTHORIZED, "UNAUTHENTICATED", "X-Employee-ID khong duoc chap nhan ngoai demo mode.")
        if x_employee_id == "EXPIRED_TOKEN":
            _event_logger.emit("authentication_failed", reason="token_expired", correlation_id=correlation_id)
            raise _error(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "Token phien dang nhap da het han.")
        raw_credential = x_employee_id
        auth_source = "demo"

    if not raw_credential:
        _event_logger.emit("authentication_failed", reason="no_credential", correlation_id=correlation_id)
        raise _error(status.HTTP_401_UNAUTHORIZED, "UNAUTHENTICATED", "Khong co hoac token khong hop le.")

    fail_for = {"IAM_ERROR"}
    try:
        employee = EmployeeContextService(
            _employee_sso_adapter(fail_for=fail_for),
            _employee_iam_adapter(fail_for=fail_for),
        ).get(raw_credential, correlation_id=correlation_id)
    except UpstreamUnavailableError:
        metrics.increment("security.authorization_denied")
        _event_logger.emit("authorization_denied", reason="unknown_identity", correlation_id=correlation_id)
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Nhan vien khong ton tai hoac khong duoc cap quyen truy cap.")
    except (UpstreamTimeoutError, ContextError):
        metrics.increment("security.iam_unavailable")
        _event_logger.emit("iam_unavailable", correlation_id=correlation_id)
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "IAM_SERVICE_UNAVAILABLE",
                     "Khong the ket noi den he thong xac thuc IAM tai thoi diem nay.", retryable=True)

    role_value = map_enterprise_role_to_role_type(employee.role, employee.organization_unit)
    identity = VerifiedIdentity(
        employee_id=employee.employee_id,
        session_id=session_id,
        roles=[RoleType(role_value)],
        permissions=employee.permissions,
        customer_scope=list(employee.access_scope.get("managed_customer_ids", [])),
        organization_unit=employee.organization_unit,
        auth_source=auth_source,
        identity_verified=True,
    )
    _event_logger.emit(
        "identity_verified", employee_id=identity.employee_id, role=role_value,
        auth_source=auth_source, correlation_id=correlation_id,
    )
    return identity


def require_capability(identity: VerifiedIdentity, capability: str) -> None:
    """Revalidate a capability at the point of use: IAM-granted permission
    AND role policy must both allow it. Never a cached snapshot -- backed
    by the identity resolved fresh on this request."""
    role = identity.roles[0]
    if capability not in identity.permissions or not has_capability(role, capability):
        metrics.increment("security.authorization_denied")
        _event_logger.emit(
            "authorization_denied", employee_id=identity.employee_id,
            capability=capability, reason="capability_not_granted",
        )
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", f"Ban khong co quyen '{capability}'.")


@router.get("", response_model=Dict[str, Any])
def get_my_profile(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, Any]:
    return identity.model_dump(mode="json")


@router.get("/context", response_model=EmployeeContextSnapshot)
def get_my_context(identity: VerifiedIdentity = Depends(require_verified_identity)) -> EmployeeContextSnapshot:
    """Assembles the complete Employee Context Snapshot with Provenance mapping."""
    emp_id = identity.employee_id
    now = datetime.now(timezone.utc)

    # 1. Authorization Context -- entirely from the verified identity, never
    # re-derived from the personalization store.
    auth_ctx = AuthorizationContext(
        identity_verified=True,
        roles=identity.roles,
        permissions=identity.permissions,
        customer_scope=identity.customer_scope,
        verified_at=now,
        expires_at=now + timedelta(hours=1),
    )

    # 2. Personalization & Fallback Logic (fail-soft: a personalization
    # store failure must never touch identity/customer_scope above).
    personalization_enabled = True
    preferences: Dict[str, Any] = {}
    confirmed_habits: List[HabitModel] = []
    personalization_degraded = False

    try:
        consent = get_consent(emp_id)
        if consent:
            personalization_enabled = consent["personalization_enabled"]
        if personalization_enabled:
            preferences = get_preferences(emp_id)
            confirmed_habits = [h for h in get_habits(emp_id) if h.status == HabitStatus.CONFIRMED]
    except Exception as exc:
        logger.error(f"Personalization database failed, falling back to default UI: {exc}")
        metrics.increment("reliability.personalization_degraded")
        _event_logger.emit("personalization_degraded", employee_id=emp_id, reason=str(exc)[:200])
        personalization_enabled = False
        personalization_degraded = True
        preferences = {
            "default_case_view": "dashboard",
            "preferred_email_template": "default",
            "show_evidence_expanded": False,
        }

    p_ctx = PersonalizationContext(
        enabled=personalization_enabled,
        preferences=preferences,
        confirmed_habits=confirmed_habits,
        context_version=1,
        personalization_degraded=personalization_degraded,
    )

    # 3. Work Context (derived from active DB state).
    work_ctx = WorkContext(
        active_case_id=None,
        assigned_customer_ids=identity.customer_scope,
        pending_task_ids=[],
        blocked_case_ids=[],
        waiting_for_roles=[],
    )
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT case_id FROM cases WHERE employee_id = ? ORDER BY updated_at DESC LIMIT 1", (emp_id,))
        case_row = cursor.fetchone()
        if case_row:
            work_ctx.active_case_id = case_row["case_id"]
        cursor.execute("SELECT item_id FROM employee_work_items WHERE employee_id = ? AND status != 'completed'", (emp_id,))
        work_ctx.pending_task_ids = [r["item_id"] for r in cursor.fetchall()]
        cursor.execute("SELECT case_id FROM cases WHERE state_json->>'status' = 'blocked'")
        work_ctx.blocked_case_ids = [r["case_id"] for r in cursor.fetchall()]
        # Which specialist subtype(s) this employee's own pending_review
        # cases are actually waiting on -- derived from the SAME
        # risk_gate_result.required_reviewer_roles the specialist-reviews
        # endpoint (case_action_router) uses to decide who may clear them,
        # not a hardcoded "always legal_specialist" guess (see
        # docs/EMPLOYEE_ROLE_DESIGN_EVALUATION_REPORT.md §9).
        cursor.execute(
            "SELECT state_json FROM cases WHERE employee_id = ? AND state_json->>'status' = 'pending_review'",
            (emp_id,),
        )
        waiting_roles: set[str] = set()
        for r in cursor.fetchall():
            state = r["state_json"]  # JSONB -> already a dict
            risk_result = (state.get("risk_gate_result") if isinstance(state, dict) else {}) or {}
            waiting_roles.update(risk_result.get("required_reviewer_roles") or ["legal_specialist"])
        work_ctx.waiting_for_roles = sorted(waiting_roles)
        conn.close()
    except Exception as exc:
        logger.warning(f"Failed to query active work context: {exc}")

    # 4. Provenance Mapping
    provenance_map = {
        "authorization_context.roles": ProvenanceMetadata(
            source="iam_sso_portal", source_version="v1.2", refreshed_at=now,
            expires_at=now + timedelta(hours=1), confidence=1.0, type=ProvenanceType.VERIFIED,
        ),
        "authorization_context.permissions": ProvenanceMetadata(
            source="iam_sso_portal", source_version="v1.2", refreshed_at=now,
            confidence=1.0, type=ProvenanceType.VERIFIED,
        ),
        "work_context.active_case_id": ProvenanceMetadata(
            source="case_repository", source_version="v2.1", refreshed_at=now,
            confidence=1.0, type=ProvenanceType.VERIFIED,
        ),
        "personalization_context.preferences": ProvenanceMetadata(
            source="personalization_store", source_version="1", refreshed_at=now,
            confidence=0.9 if not personalization_degraded else 0.0,
            type=ProvenanceType.PREFERENCE,
        ),
    }

    return EmployeeContextSnapshot(
        employee_id=emp_id,
        authorization_context=auth_ctx,
        work_context=work_ctx,
        personalization_context=p_ctx,
        provenance_map=provenance_map,
        generated_at=now,
    )


@router.get("/work-queue", response_model=List[Any])
def get_my_work_queue(identity: VerifiedIdentity = Depends(require_verified_identity)) -> List[Any]:
    """Calculates Next Best Work queue for the employee."""
    conn = get_db_connection()
    try:
        nbw_list = get_next_best_work(
            employee_id=identity.employee_id,
            role=identity.roles[0],
            permissions=identity.permissions,
            customer_scope=identity.customer_scope,
            conn=conn,
        )
    finally:
        conn.close()
    _event_logger.emit("next_best_work_ranked", employee_id=identity.employee_id, count=len(nbw_list))
    return nbw_list


@router.get("/preferences", response_model=Dict[str, Any])
def get_my_preferences(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, Any]:
    return get_preferences(identity.employee_id)


@router.patch("/preferences", response_model=Dict[str, Any])
def patch_my_preferences(prefs: Dict[str, Any], identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, Any]:
    save_preferences(identity.employee_id, prefs)
    _event_logger.emit("preference_updated", employee_id=identity.employee_id, keys=list(prefs.keys()))
    return get_preferences(identity.employee_id)


@router.get("/habits", response_model=List[HabitModel])
def get_my_habits(identity: VerifiedIdentity = Depends(require_verified_identity)) -> List[HabitModel]:
    return get_habits(identity.employee_id)


@router.post("/habits/{habit_id}/confirm")
def post_confirm_habit(habit_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    success = confirm_habit(identity.employee_id, habit_id)
    if success:
        _event_logger.emit("habit_confirmed", employee_id=identity.employee_id, habit_id=habit_id)
    return {"success": success}


@router.post("/habits/{habit_id}/reject")
def post_reject_habit(habit_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    success = reject_habit(identity.employee_id, habit_id)
    return {"success": success}


@router.delete("/habits/{habit_id}")
def delete_my_habit(habit_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    success = delete_habit(identity.employee_id, habit_id)
    if success:
        _event_logger.emit("habit_deleted", employee_id=identity.employee_id, habit_id=habit_id)
    return {"success": success}


@router.get("/personalization", response_model=Dict[str, Any])
def get_my_personalization(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, Any]:
    consent = get_consent(identity.employee_id)
    if not consent:
        return {
            "enabled": True, "activity_learning_enabled": False,
            "allowed_event_categories": [], "consent_version": "v1",
            "personalization_degraded": False,
        }
    return {
        "enabled": consent["personalization_enabled"],
        "activity_learning_enabled": consent["activity_learning_enabled"],
        "allowed_event_categories": consent["allowed_event_categories"],
        "consent_version": consent["consent_version"],
        "personalization_degraded": False,
    }


@router.post("/personalization/enable")
def post_enable_personalization(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    return _set_personalization(identity.employee_id, True)


@router.post("/personalization/disable")
def post_disable_personalization(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    return _set_personalization(identity.employee_id, False)


def _set_personalization(employee_id: str, enabled: bool) -> Dict[str, bool]:
    consent = get_consent(employee_id)
    model = ConsentModel(
        employee_id=employee_id,
        personalization_enabled=enabled,
        activity_learning_enabled=consent["activity_learning_enabled"] if consent else enabled,
        allowed_event_categories=consent["allowed_event_categories"] if consent else [],
        consent_version=consent["consent_version"] if consent else "v1",
        confirmed_at=datetime.now(timezone.utc),
    )
    save_consent(model)
    _event_logger.emit(
        "personalization_enabled" if enabled else "personalization_disabled",
        employee_id=employee_id,
    )
    return {"success": True}


# --- Recommendation feedback -----------------------------------------------
# Registered on a dedicated, correctly-mounted router (see app/main.py:
# app.include_router(recommendation_router, prefix="/api/v2")) so the final
# path is exactly /api/v2/recommendations/{id}/... . The previous version
# of this file registered these on a throwaway `APIRouter()` instance that
# was never included anywhere, so all three 404'd unconditionally -- see
# docs/ROLE_AWARE_REPO_VERIFICATION_REPORT.md §14.

_VALID_FEEDBACK = {"accepted", "edited", "rejected", "not_applicable"}


class RecommendationFeedbackBody(BaseModel):
    feedback: str
    original: Optional[Dict[str, Any]] = None
    edited: Optional[Dict[str, Any]] = None


def _submit_feedback(rec_id: str, identity: VerifiedIdentity, feedback: str,
                      orig_val: Optional[Dict[str, Any]] = None, edit_val: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    if feedback not in _VALID_FEEDBACK:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_FEEDBACK", f"feedback phai la mot trong {sorted(_VALID_FEEDBACK)}")
    save_recommendation_feedback(
        feedback_id=f"FEEDBACK-{rec_id}-{identity.employee_id}",
        employee_id=identity.employee_id, rec_id=rec_id, feedback=feedback,
        orig_val=orig_val, edit_val=edit_val,
    )
    _event_logger.emit(f"recommendation_{feedback}", employee_id=identity.employee_id, recommendation_id=rec_id)
    return {"success": True}


@recommendation_router.post("/{rec_id}/accept")
def post_accept_recommendation(rec_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    return _submit_feedback(rec_id, identity, "accepted")


@recommendation_router.post("/{rec_id}/edit")
def post_edit_recommendation(rec_id: str, payload: Dict[str, Any], identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    return _submit_feedback(rec_id, identity, "edited", payload.get("original"), payload.get("edited"))


@recommendation_router.post("/{rec_id}/reject")
def post_reject_recommendation(rec_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    return _submit_feedback(rec_id, identity, "rejected")


@recommendation_router.post("/{rec_id}/feedback")
def post_recommendation_feedback(rec_id: str, body: RecommendationFeedbackBody, identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, bool]:
    """Unified alternative to accept/edit/reject, per spec §8.3."""
    return _submit_feedback(rec_id, identity, body.feedback, body.original, body.edited)


# --- Manager Dashboard -------------------------------------------------------
@router.get("/team/workload", tags=["Manager Console"])
def get_team_workload(identity: VerifiedIdentity = Depends(require_verified_identity)) -> Dict[str, Any]:
    """Manager console view: Aggregate dashboard only. Strictly isolation of individual RM preferences."""
    if RoleType.MANAGER not in identity.roles:
        metrics.increment("security.authorization_denied")
        _event_logger.emit("authorization_denied", employee_id=identity.employee_id, reason="not_manager")
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Ban khong co quyen truy cap Manager Dashboard.")
    require_capability(identity, "team:view_workload")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS n FROM cases WHERE state_json->>'status' = 'blocked'")
        blocked_count = cursor.fetchone()["n"]
    except Exception:
        # `cases` belongs to V2Repository's schema, not this module's --
        # tolerate any query issue rather than 500ing the whole dashboard.
        # A failed statement aborts the PostgreSQL transaction, so roll back
        # before issuing the remaining queries on this connection.
        conn.rollback()
        blocked_count = 0
    cursor.execute("SELECT COUNT(*) AS n FROM employee_work_items WHERE status != 'completed' AND urgency >= 0.8")
    sla_breaches = cursor.fetchone()["n"]
    cursor.execute("SELECT feedback, COUNT(*) AS c FROM employee_recommendation_feedback GROUP BY feedback")
    utilization = {r["feedback"]: r["c"] for r in cursor.fetchall()}
    cursor.execute("SELECT COUNT(DISTINCT employee_id) AS n FROM employee_personas")
    cohort_size = cursor.fetchone()["n"]
    conn.close()

    return {
        "branch_id": "BRANCH-HN-01",
        "cohort_size": cohort_size,
        "aggregate_metrics": {
            "blocked_cases": blocked_count,
            "sla_risks": sla_breaches,
            "ai_recommendation_utilization": {
                "cohort_minimum_size_met": cohort_size >= 5,
                "utilization_summary": utilization,
            },
        },
    }


# --- Specialist Review (Product/Legal/Credit act on a case) ----------------
# Closes docs/EMPLOYEE_ROLE_DESIGN_EVALUATION_REPORT.md gap #1/#2/#3:
# previously every case-mutating endpoint in app/api/v2/router.py was
# owned()-gated (RM-only); a specialist could see a work-queue item but had
# no endpoint to act on it, and a PENDING_REVIEW case had no defined human
# resolver at all.
#
# Scope of this round (see docs/... implementation report for full reasoning):
#   - Legal Specialist and Product Specialist get REAL case-status-changing
#     power, but ONLY over the exact reason RiskGuardrailGate blocked the
#     case (RiskGateDecision.required_reviewer_roles, derived from
#     Evidence.module + eligibility outcome) -- never a blanket "any
#     specialist can clear anything" grant.
#   - Credit Specialist resolves only a Credit-owned review requirement;
#     it cannot clear Product or Legal constraints and never approves credit.
#   - A multi-domain block (e.g. both Product AND Legal evidence invalid)
#     requires EVERY named role to clear before the case advances --
#     cleared_roles_for_case_version() stops one specialist from unilaterally
#     clearing a block that is only partly theirs to resolve.


def _reviewer_capability(role: RoleType, decision: str) -> str:
    if role == RoleType.LEGAL_SPECIALIST:
        return "legal:block_non_eligible" if decision == "blocked" else "legal:check_issue"
    if role == RoleType.PRODUCT_SPECIALIST:
        return "product:verify_fit"
    if role == RoleType.CREDIT_SPECIALIST:
        return "credit:review_structure"
    raise ValueError(f"unsupported specialist role: {role.value}")


def _notification_item_id(
    *, case_id: str, case_version: int, event_type: str, target_employee_id: str, role_set: List[str],
) -> str:
    """Deterministic (not random-per-request) work-item id, so a genuine
    retry -- client timeout-and-resend, two specialists finishing within
    the same case_version -- REPLACES the same notification row instead of
    creating a duplicate (create_work_item does INSERT OR REPLACE keyed on
    item_id). Keyed on exactly the facts that make two notifications "the
    same event": which case+version, what kind of outcome, who it is for,
    and which role-set it was resolving (so a later, different block on the
    same case_version -- rare, but possible if a second issue is found --
    still gets its own row)."""
    role_hash = hashlib.sha256(",".join(sorted(role_set)).encode("utf-8")).hexdigest()[:12]
    return f"REVIEW-NOTIFY-{case_id}-{case_version}-{event_type}-{target_employee_id}-{role_hash}"


def _notify_rm(
    state_value: Any, *, item_id: str, title: str, urgency: float, risk_severity: float,
) -> None:
    """Surfaces a completed specialist review back into the owning RM's
    existing Next Best Work queue -- the real "specialist -> RM return path"
    the role design evaluation report found missing, built on the same
    employee_work_items table/ranking engine the RM already watches rather
    than inventing a second, parallel notification channel."""
    create_work_item(
        {
            "item_id": item_id,
            "employee_id": state_value.context.employee.employee_id,
            "title": title,
            "urgency": urgency,
            "risk_severity": risk_severity,
            "business_impact": 0.6,
            "customer_commitment": 0.3,
            "dependency_unblock": 0.5,
            "ownership_match": 1.0,
            "estimated_effort": 0.2,
            "dependency_ids": [],
            "role_required": RoleType.RM.value,
            "customer_id": str(state_value.context.customer.customer_id),
        }
    )


@case_action_router.get("/{case_id}/review-context")
def get_case_review_context(
    case_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)
) -> Dict[str, Any]:
    """The minimum a specialist needs to write an informed review: current
    blocking reasons and the specific evidence claims involved -- not the
    full case (customer PII / full audit trail stay out of scope, matching
    the least-data-necessary finding in the role design evaluation report).
    Without this, a specialist had no way to even discover the evidence_ids
    a review is supposed to reference."""
    stored = _repo().get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state
    if state_value.context.customer.customer_id not in identity.customer_scope:
        metrics.increment("security.case_scope_denied")
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Case ngoai pham vi khach hang duoc giao.")
    risk_result = state_value.risk_gate_result or {}
    return {
        "case_id": case_id,
        "case_version": stored.version,
        "case_status": state_value.status.value,
        "customer_id": state_value.context.customer.customer_id,
        "required_reviewer_roles": risk_result.get("required_reviewer_roles", []),
        "reasons": risk_result.get("reasons", []),
        "triggered_rules": risk_result.get("triggered_rules", []),
        "cleared_roles": cleared_roles_for_case_version(case_id, stored.version),
        "evidences": [
            {
                "claim_id": item.claim_id,
                "module": item.module,
                "claim": item.claim,
                "source_document_id": item.source_document_id,
                "quote": item.quote,
                "is_valid": item.is_valid,
            }
            for item in state_value.evidences
        ],
    }


@case_action_router.get("/{case_id}/specialist-reviews", response_model=List[SpecialistReviewRecord])
def get_case_specialist_reviews(
    case_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)
) -> List[SpecialistReviewRecord]:
    stored = _repo().get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state
    is_owner = state_value.context.employee.employee_id == identity.employee_id
    in_scope = state_value.context.customer.customer_id in identity.customer_scope
    if not (is_owner or in_scope):
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen xem case nay.")
    return [SpecialistReviewRecord(**row) for row in list_specialist_reviews(case_id)]


@case_action_router.post(
    "/{case_id}/specialist-reviews",
    response_model=SpecialistReviewResult,
    status_code=status.HTTP_201_CREATED,
)
def submit_specialist_review(
    case_id: str,
    body: SpecialistReviewRequest,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> SpecialistReviewResult:
    role = identity.roles[0]
    if role != body.review_type:
        metrics.increment("security.authorization_denied")
        _event_logger.emit(
            "authorization_denied", employee_id=identity.employee_id, case_id=case_id,
            reason="review_type_role_mismatch", claimed_review_type=body.review_type.value,
        )
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Vai tro cua ban khong khop review_type.")
    require_capability(identity, _reviewer_capability(role, body.decision))

    if body.decision == "blocked" and not body.findings:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "FINDINGS_REQUIRED",
                     "Quyet dinh 'blocked' yeu cau it nhat mot finding.")
    if body.decision == "needs_more_information" and not body.required_information:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "REQUIRED_INFORMATION_REQUIRED",
                     "Quyet dinh 'needs_more_information' yeu cau required_information.")

    repo = _repo()
    stored = repo.get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state

    if state_value.context.customer.customer_id not in identity.customer_scope:
        metrics.increment("security.case_scope_denied")
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Case ngoai pham vi khach hang duoc giao.")
    if state_value.status != CaseStatus.PENDING_REVIEW:
        raise _error(status.HTTP_409_CONFLICT, "CASE_NOT_PENDING_REVIEW",
                     "Case hien khong o trang thai cho specialist review.")
    if body.expected_case_version is not None and body.expected_case_version != stored.version:
        raise _error(
            status.HTTP_409_CONFLICT, "CASE_VERSION_CONFLICT",
            f"Case da doi tu version {body.expected_case_version} sang {stored.version}; "
            "hay tai lai /review-context truoc khi gui lai.",
            retryable=True,
        )

    known_claim_ids = {item.claim_id for item in state_value.evidences}
    unknown_evidence = [eid for eid in body.evidence_ids if eid not in known_claim_ids]
    if unknown_evidence:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNKNOWN_EVIDENCE_ID",
                     f"evidence_ids khong ton tai tren case: {unknown_evidence}")

    risk_result = state_value.risk_gate_result or {}
    required_roles = set(risk_result.get("required_reviewer_roles") or ["legal_specialist"])

    if role in {RoleType.LEGAL_SPECIALIST, RoleType.PRODUCT_SPECIALIST, RoleType.CREDIT_SPECIALIST}:
        if role.value not in required_roles:
            raise _error(status.HTTP_409_CONFLICT, "SPECIALIST_REVIEW_NOT_APPLICABLE",
                         "Case hien khong cho review tu vai tro nay.")
        advisory_only = False
        if body.decision == "cleared":
            # The single most safety-critical check in this endpoint: a
            # specialist may only clear a block the deterministic engine
            # (or the eligibility rule registry, via
            # EligibilityRule.human_review_allowed) has explicitly marked
            # human-overridable. Missing mandatory documents, absolute
            # numeric thresholds, bad-debt history, an unresolved evidence
            # citation failure, or an unrecognized status all default to
            # NOT overridable -- see app/workflow/risk_gate.py.
            if not risk_result.get("human_review_allowed"):
                metrics.increment("security.override_denied")
                _event_logger.emit(
                    "specialist_override_denied", employee_id=identity.employee_id, case_id=case_id,
                    review_type=role.value, reasons=risk_result.get("reasons", []),
                    triggered_rules=risk_result.get("triggered_rules", []),
                )
                raise _error(
                    status.HTTP_409_CONFLICT, "BLOCK_NOT_OVERRIDABLE",
                    "Ly do chan case nay khong duoc phep gia han boi specialist "
                    "(rule/evidence bat buoc, khong phai judgment call).",
                )
            if not body.findings:
                raise _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "FINDINGS_REQUIRED",
                    "Gia han (cleared) mot block phai co it nhat mot finding lam can cu.",
                )
    else:  # Defensive only; request schema rejects non-specialist roles first.
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Vai tro khong duoc phep review case.")

    review_id = f"REVIEW-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    case_status_changed = False
    still_waiting_for: List[str] = []
    notify_title: Optional[str] = None
    notify_urgency = 0.5
    notify_risk = 0.4
    notify_event_type: Optional[str] = None

    if advisory_only:
        if body.decision != "cleared":
            notify_title = f"Operations ghi nhan '{body.decision}' tren case {case_id}: {body.summary}"
            notify_event_type = f"advisory_{body.decision}"
    elif body.decision == "blocked":
        state_value.status = transition(state_value.status, CaseStatus.REJECTED)
        state_value.approval.status = ApprovalStatus.REJECTED
        state_value.audit_events.append(
            {
                "actor": identity.employee_id, "action": "case_rejected_by_specialist_review",
                "at": now.isoformat(),
                "payload": {"review_id": review_id, "review_type": role.value, "summary": body.summary},
            }
        )
        case_status_changed = True
        notify_title = f"Case {case_id} bi {role.value} tu choi: {body.summary}"
        notify_urgency, notify_risk = 0.9, 0.8
        notify_event_type = "blocked"
    elif body.decision == "needs_more_information":
        state_value.status = transition(state_value.status, CaseStatus.IN_ANALYSIS)
        state_value.status = transition(state_value.status, CaseStatus.PENDING_INFORMATION)
        for info in body.required_information:
            state_value.next_best_questions.append(
                NextBestQuestion(
                    question_id=f"NBQ-{uuid.uuid4().hex[:10].upper()}",
                    question=f"{role.value} yeu cau bo sung: {info}",
                    reason=body.summary,
                    target_field=f"specialist_review.{info}",
                    source_gap=info,
                    decision_impact="high",
                    priority=1,
                    answer_type="value",
                    blocking_steps=["specialist_review"],
                ).model_dump(mode="json")
            )
        state_value.audit_events.append(
            {
                "actor": identity.employee_id, "action": "specialist_requested_more_information",
                "at": now.isoformat(),
                "payload": {
                    "review_id": review_id, "review_type": role.value,
                    "required_information": body.required_information,
                },
            }
        )
        case_status_changed = True
        notify_title = f"Case {case_id} can bo sung thong tin theo yeu cau cua {role.value}"
        notify_urgency, notify_risk = 0.8, 0.5
        notify_event_type = "needs_more_information"
    else:  # cleared, and role is a named required reviewer for this case
        previously_cleared = set(cleared_roles_for_case_version(case_id, stored.version))
        still_waiting_for = sorted(required_roles - previously_cleared - {role.value})
        if not still_waiting_for:
            engine = V2WorkflowEngine()
            state_value = engine.clear_specialist_block(state_value)
            case_status_changed = True
            notify_title = f"Case {case_id} da duoc {role.value} thong qua -- san sang phe duyet"
            notify_urgency, notify_risk = 0.7, 0.3
            notify_event_type = "cleared"

    save_specialist_review(
        review_id=review_id, case_id=case_id, case_version=stored.version,
        reviewer_employee_id=identity.employee_id, review_type=role.value,
        decision=body.decision, summary=body.summary,
        findings=[f.model_dump(mode="json") for f in body.findings],
        required_information=body.required_information, evidence_ids=body.evidence_ids,
        case_status_changed=case_status_changed, advisory_only=advisory_only,
    )

    final_version = stored.version
    if case_status_changed:
        repo.append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=identity.employee_id, action=f"specialist_review_{body.decision}",
            payload={
                "review_id": review_id, "review_type": role.value, "summary": body.summary,
                "overridden_reasons": risk_result.get("reasons", []),
                "overridden_rules": risk_result.get("triggered_rules", []),
                "findings": [f.model_dump(mode="json") for f in body.findings],
            },
        )
        try:
            updated = repo.save_case(state_value, expected_version=stored.version)
        except StateConflictError as exc:
            raise _error(status.HTTP_409_CONFLICT, "STATE_VERSION_CONFLICT", str(exc), retryable=True) from exc
        final_version = updated.version

    _event_logger.emit(
        "specialist_review_submitted", employee_id=identity.employee_id, case_id=case_id,
        review_type=role.value, decision=body.decision, case_status_changed=case_status_changed,
        advisory_only=advisory_only, still_waiting_for=still_waiting_for,
    )
    if notify_title and notify_event_type:
        item_id = _notification_item_id(
            case_id=case_id, case_version=stored.version, event_type=notify_event_type,
            target_employee_id=state_value.context.employee.employee_id, role_set=sorted(required_roles),
        )
        _notify_rm(state_value, item_id=item_id, title=notify_title, urgency=notify_urgency, risk_severity=notify_risk)

    return SpecialistReviewResult(
        review_id=review_id, case_id=case_id, case_version=final_version,
        reviewer_employee_id=identity.employee_id, review_type=role, decision=body.decision,
        summary=body.summary, case_status=state_value.status.value, case_status_changed=case_status_changed,
        advisory_only=advisory_only, still_waiting_for=still_waiting_for, created_at=now,
    )


# --- Operational Readiness (RM-owned deterministic operations surface) -----
# A separate, manual domain object -- NOT the same thing as
# app/operations/service.py's OperationsService checklist, which recomputes
# itself from document status on every analysis run and therefore cannot be
# durably "checked off" by a person. This is the real, human-maintained
# readiness tracker the role design evaluation report's Operations gap
# actually called for -- it never touches CaseStatus or legal/product
# eligibility, matching the separation of duties already enforced for
# specialist-reviews above.

@case_action_router.get("/{case_id}/operational-readiness", response_model=Optional[OperationalReadinessSnapshot])
def get_operational_readiness_endpoint(
    case_id: str, identity: VerifiedIdentity = Depends(require_verified_identity)
) -> Optional[OperationalReadinessSnapshot]:
    stored = _repo().get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state
    is_owner = state_value.context.employee.employee_id == identity.employee_id
    in_scope = state_value.context.customer.customer_id in identity.customer_scope
    if not (is_owner or in_scope):
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen xem case nay.")
    row = get_operational_readiness(case_id)
    return OperationalReadinessSnapshot(**row) if row else None


@case_action_router.put("/{case_id}/operational-readiness", response_model=OperationalReadinessSnapshot)
def put_operational_readiness(
    case_id: str,
    body: OperationalReadinessRequest,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> OperationalReadinessSnapshot:
    if RoleType.RM not in identity.roles:
        metrics.increment("security.authorization_denied")
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chi RM phu trach case duoc cap nhat readiness.")
    require_capability(identity, "case:write")

    stored = _repo().get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state
    if state_value.context.customer.customer_id not in identity.customer_scope:
        metrics.increment("security.case_scope_denied")
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Case ngoai pham vi khach hang duoc giao.")

    overall_status = "ready" if all(item.status == "completed" for item in body.items) else "not_ready"
    save_operational_readiness(
        case_id=case_id, status=overall_status,
        items=[item.model_dump(mode="json") for item in body.items],
        summary=body.summary, updated_by=identity.employee_id,
    )
    _event_logger.emit(
        "operational_readiness_updated", employee_id=identity.employee_id, case_id=case_id,
        status=overall_status, item_count=len(body.items),
    )
    if overall_status == "not_ready":
        blocked_codes = [item.code for item in body.items if item.status != "completed"]
        item_id = _notification_item_id(
            case_id=case_id, case_version=stored.version, event_type="operational_readiness_not_ready",
            target_employee_id=state_value.context.employee.employee_id, role_set=["relationship_manager"],
        )
        _notify_rm(
            state_value, item_id=item_id,
            title=f"Van hanh: case {case_id} chua san sang thuc thi -- con thieu {', '.join(blocked_codes)}",
            urgency=0.6, risk_severity=0.4,
        )
    row = get_operational_readiness(case_id)
    return OperationalReadinessSnapshot(**row)


# --- Agent Knowledge Console (department Specialist controls their own -----
# domain's Agent knowledge base) -------------------------------------------
# A specialist may only ever read/feed/update knowledge for their OWN
# domain's Agent -- Product Specialist -> ProductExpertAgent's knowledge,
# Credit Specialist -> CreditExpertAgent's, Insurance Specialist ->
# InsuranceExpertAgent's -- enforced by DOMAIN_BY_ROLE (never a body/query
# parameter). Reuses the existing KnowledgeChunk/PersistentHybridIndex
# storage each of the three domain services already indexes into; this is
# not a new knowledge store.

_VERSION_SUFFIX = re.compile(r"::v\d+$")
_AGENT_COMPONENT_BY_DOMAIN = {
    "product": {"ProductExpert", "ProductExpertAgent"},
    "legal": {"LegalExpert", "LegalComplianceAgent"},
    "credit": {"CreditExpert", "CreditExpertAgent"},
    "insurance": {"InsuranceExpert", "InsuranceExpertAgent"},
}
# V2WorkflowEngine._product_evidence()/_legal_evidence() (app/workflow/engine.py)
# tag Evidence.module as "Product"/"Eligibility" -- "Eligibility" because
# that node evaluates product eligibility, not a "Legal" label -- and there
# Credit evidence is carried by typed ExpertFinding.evidence_refs rather
# than the legacy state.evidences list.
_EVIDENCE_MODULE_BY_DOMAIN = {"product": "product", "legal": "eligibility", "credit": None, "insurance": None}


def _domain_for(identity: VerifiedIdentity) -> AgentDomain:
    role = identity.roles[0]
    domain = DOMAIN_BY_ROLE.get(role)
    if domain is None:
        raise _error(
            status.HTTP_403_FORBIDDEN, "FORBIDDEN",
            "Vai tro cua ban khong quan ly tri thuc cho Agent nao.",
        )
    return domain


def _knowledge_service_for(domain: AgentDomain):
    if domain == "product":
        return ProductKnowledgeService()
    if domain == "legal":
        return LegalKnowledgeService()
    if domain == "credit":
        return CreditKnowledgeService()
    return InsuranceKnowledgeService()


def _to_knowledge_record(chunk: KnowledgeChunk, domain: AgentDomain) -> KnowledgeEntryRecord:
    return KnowledgeEntryRecord(
        chunk_id=chunk.chunk_id, domain=domain, document_id=chunk.document_id,
        document_version=chunk.document_version, product_id=chunk.product_id,
        section_path=chunk.section_path, chunk_type=chunk.chunk_type, text=chunk.text,
        effective_from=chunk.effective_from, effective_to=chunk.effective_to,
        is_superseded=chunk.is_superseded, is_quarantined=chunk.is_quarantined,
        authority_tier=chunk.authority_tier.value if chunk.authority_tier else None,
        verification_status=chunk.verification_status.value if chunk.verification_status else None,
        contributed_by=chunk.contributed_by, contributed_at=chunk.contributed_at,
    )


@knowledge_router.get("", response_model=List[KnowledgeEntryRecord])
def list_agent_knowledge(
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[KnowledgeEntryRecord]:
    domain = _domain_for(identity)
    service = _knowledge_service_for(domain)
    chunks = service.index.list_chunks()
    chunks.sort(key=lambda c: c.contributed_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return [_to_knowledge_record(c, domain) for c in chunks]


@knowledge_router.post("", response_model=KnowledgeEntryRecord, status_code=status.HTTP_201_CREATED)
def create_agent_knowledge_entry(
    body: KnowledgeEntryCreateRequest,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> KnowledgeEntryRecord:
    domain = _domain_for(identity)
    require_capability(identity, MANAGE_CAPABILITY_BY_DOMAIN[domain])

    service = _knowledge_service_for(domain)
    now = datetime.now(timezone.utc)
    chunk_id = f"SPEC-{domain.upper()}-{uuid.uuid4().hex[:10].upper()}"
    document_id = body.document_id or f"SPEC-CONTRIB-{identity.employee_id}"
    chunk = KnowledgeChunk(
        chunk_id=chunk_id, document_id=document_id, document_version="1",
        product_id=body.product_id, section_path=body.section_path,
        chunk_type=body.chunk_type or default_chunk_type(domain), text=body.text,
        effective_from=body.effective_from, effective_to=body.effective_to, active=True,
        segments=[], access_scope={"branches": ["*"]},
        content_hash=hashlib.sha256(body.text.encode("utf-8")).hexdigest(),
        source_type="specialist_contributed",
        authority_tier=AuthorityTier.TIER_2_VERIFIED_INTERNAL,
        verification_status=VerificationStatus.VERIFIED,
        contributed_by=identity.employee_id, contributed_at=now,
    )
    service.index.upsert(
        [chunk], source_hash=chunk.content_hash, dataset_version=f"specialist-{now.date().isoformat()}",
    )
    _event_logger.emit(
        "agent_knowledge_entry_created", employee_id=identity.employee_id, domain=domain,
        chunk_id=chunk_id, product_id=body.product_id,
    )
    return _to_knowledge_record(chunk, domain)


@knowledge_router.patch("/{chunk_id}", response_model=KnowledgeEntryRecord)
def update_agent_knowledge_entry(
    chunk_id: str,
    body: KnowledgeEntryUpdateRequest,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> KnowledgeEntryRecord:
    domain = _domain_for(identity)
    require_capability(identity, MANAGE_CAPABILITY_BY_DOMAIN[domain])
    service = _knowledge_service_for(domain)
    existing = service.index.exact_lookup_by_chunk_id(chunk_id)
    if existing is None:
        raise _error(status.HTTP_404_NOT_FOUND, "KNOWLEDGE_ENTRY_NOT_FOUND", "Khong tim thay muc tri thuc nay.")

    now = datetime.now(timezone.utc)
    dataset_version = f"specialist-{now.date().isoformat()}"

    if body.is_quarantined is not None and body.is_quarantined != existing.is_quarantined:
        existing = existing.model_copy(update={"is_quarantined": body.is_quarantined})
        service.index.upsert([existing], source_hash=existing.content_hash, dataset_version=dataset_version)
        _event_logger.emit(
            "agent_knowledge_entry_quarantine_toggled", employee_id=identity.employee_id, domain=domain,
            chunk_id=chunk_id, is_quarantined=body.is_quarantined,
        )

    if body.text is None:
        if body.effective_to is not None and body.effective_to != existing.effective_to:
            existing = existing.model_copy(update={"effective_to": body.effective_to})
            service.index.upsert([existing], source_hash=existing.content_hash, dataset_version=dataset_version)
        return _to_knowledge_record(existing, domain)

    # Text change: never overwritten in place -- the old chunk is kept and
    # marked is_superseded so its history stays inspectable/citable, and a
    # new versioned chunk_id carries the updated text forward.
    try:
        next_version = int(existing.document_version) + 1
    except ValueError:
        next_version = 2
    base_chunk_id = _VERSION_SUFFIX.sub("", chunk_id)
    new_chunk_id = f"{base_chunk_id}::v{next_version}"
    superseded = existing.model_copy(update={"is_superseded": True})
    new_chunk = existing.model_copy(update={
        "chunk_id": new_chunk_id,
        "document_version": str(next_version),
        "text": body.text,
        "effective_to": body.effective_to if body.effective_to is not None else existing.effective_to,
        "content_hash": hashlib.sha256(body.text.encode("utf-8")).hexdigest(),
        "is_superseded": False,
        "contributed_by": identity.employee_id,
        "contributed_at": now,
    })
    service.index.upsert([superseded, new_chunk], source_hash=new_chunk.content_hash, dataset_version=dataset_version)
    _event_logger.emit(
        "agent_knowledge_entry_updated", employee_id=identity.employee_id, domain=domain,
        old_chunk_id=chunk_id, new_chunk_id=new_chunk_id,
    )
    return _to_knowledge_record(new_chunk, domain)


@knowledge_router.get("/activity", response_model=AgentActivitySnapshot)
def get_agent_activity(
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> AgentActivitySnapshot:
    """"Agent cua toi dang lam gi": knowledge entries this domain's Agent
    can retrieve today, plus a metadata (not full-content) summary of
    recent cases in this specialist's assigned customer_scope that Agent
    has produced a result on -- including evidence count and the Agent's
    own latest ai_decision_log entry, so the specialist sees what the
    Agent did and what it grounded that on, not just a raw case list."""
    domain = _domain_for(identity)
    service = _knowledge_service_for(domain)
    chunks = service.index.list_chunks()
    active_count = sum(1 for c in chunks if not c.is_superseded and not c.is_quarantined)

    result_field = {
        "product": "product_result",
        "legal": "eligibility_result",
        "credit": "credit_result",
        "insurance": "insurance_result",
    }[domain]
    components = _AGENT_COMPONENT_BY_DOMAIN[domain]

    stored_cases = _repo().list_cases_for_customers(identity.customer_scope)
    items: List[AgentCaseActivityItem] = []
    for stored in stored_cases[:25]:
        state_value = stored.state
        agent_result = getattr(state_value, result_field)
        agent_summary: Dict[str, Any] = {}
        if domain == "product" and agent_result:
            recs = agent_result.get("recommendations", [])
            agent_summary = {"recommendation_count": len(recs), "product_ids": [r.get("product_id") for r in recs]}
        elif domain == "legal" and agent_result:
            agent_summary = {
                "overall_status": agent_result.get("overall_status"),
                "rule_count": len(agent_result.get("rule_evaluations", [])),
            }
        elif domain == "credit" and agent_result:
            agent_summary = {
                "status": agent_result.get("status"),
                "credit_product_ids": agent_result.get("credit_product_ids", []),
                "hard_block_count": len(agent_result.get("hard_blocks", [])),
                "missing_information_count": len(agent_result.get("missing_information", [])),
                "analysis_confidence": agent_result.get("analysis_confidence"),
            }
        elif domain == "insurance" and agent_result:
            agent_summary = {
                "status": agent_result.get("status"),
                "insurance_product_ids": agent_result.get("insurance_product_ids", []),
                "coverage_check_count": len(agent_result.get("coverage_checks", [])),
                "hard_block_count": len(agent_result.get("hard_blocks", [])),
                "missing_information_count": len(agent_result.get("missing_information", [])),
            }
        evidence_module = _EVIDENCE_MODULE_BY_DOMAIN[domain]
        domain_evidence = (
            [ev for ev in state_value.evidences if ev.module.lower() == evidence_module]
            if evidence_module is not None else []
        )
        expert_evidence_count = 0
        expert_type = {"credit": "CreditExpert", "insurance": "InsuranceExpert"}.get(domain)
        if expert_type:
            expert_evidence_count = sum(
                len(finding.evidence_refs)
                for finding in state_value.expert_findings
                if finding.agent_type.value == expert_type
            )
        last_ai_log = next(
            (e for e in reversed(state_value.ai_decision_log) if e.get("component") in components), None,
        )
        items.append(
            AgentCaseActivityItem(
                case_id=state_value.case_id, case_status=state_value.status.value,
                customer_id=state_value.context.customer.customer_id,
                updated_at=state_value.updated_at, agent_has_run=agent_result is not None,
                agent_summary=agent_summary, evidence_count=len(domain_evidence) + expert_evidence_count,
                last_ai_log_event=last_ai_log,
            )
        )

    return AgentActivitySnapshot(
        domain=domain, generated_at=datetime.now(timezone.utc),
        knowledge_entry_count=len(chunks), active_knowledge_entry_count=active_count,
        cases=items,
    )
