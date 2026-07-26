"""P0 cross-role workflow surfaces that don't belong to either pipeline's
own router: case timeline, customer document requests (create/list/submit/
cancel), per-recipient notifications, and the dynamic specialist work-item
queue (GET /work-items/my).

Real triggers for these tables currently live in credit_request_router.py
(Credit Request pipeline) and employee_router.py's forward-to-specialist
endpoint (SalesCase pipeline). This router is the read/act surface for what
those triggers wrote -- it does not itself decide case or request state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.v2.employee_router import require_capability, require_verified_identity
from app.config import settings
from app.schemas.v2.employee import RoleType, VerifiedIdentity
from app.storage.credit_request_repository import CreditRequestRepository
from app.storage.employee_db import get_db_connection
from app.storage.repository import V2Repository
from app.storage.workflow_repository import WorkflowRepository

router = APIRouter(tags=["Workflow"])

_credit_repo = CreditRequestRepository()


def _error(http_status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def _workflow() -> WorkflowRepository:
    return WorkflowRepository(settings.V2_DB_PATH)


def _repo() -> V2Repository:
    return V2Repository(settings.V2_DB_PATH)


def _case_access(case_id: str, identity: VerifiedIdentity) -> None:
    """Same viewer rule already used by get_case_specialist_reviews: case
    owner OR anyone whose customer_scope contains the case's customer
    (covers staff roles AND the customer themself, since a customer's
    identity.customer_scope is their own customer_id).

    Falls back to the Credit Request pipeline's own customer_id/submitted_by
    when no SharedCaseState exists for this case_id -- CreditRequestRepository
    .create() auto-generates a case_id when the customer submits a credit
    request without a prior intake, so `cases` has no matching row at all in
    that path even though timeline/document-request rows for it are real."""
    stored = _repo().get_case(case_id)
    if stored is not None:
        state_value = stored.state
        is_owner = state_value.context.employee.employee_id == identity.employee_id
        in_scope = state_value.context.customer.customer_id in identity.customer_scope
        if is_owner or in_scope:
            return
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen xem case nay.")

    credit_rows = _credit_repo.list_by_case_id(case_id)
    if credit_rows:
        for row in credit_rows:
            if row["customer_id"] in identity.customer_scope or row["submitted_by"] == identity.employee_id:
                return
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen xem case nay.")

    raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")


# --- Timeline ----------------------------------------------------------------

@router.get("/cases/{case_id}/timeline")
def get_case_timeline(
    case_id: str, identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    _case_access(case_id, identity)
    return _workflow().list_timeline_events(case_id)


# --- Document Requests ---------------------------------------------------------

class DocumentRequestCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    customer_safe_reason: str = Field(min_length=3, max_length=1000)
    internal_reason: str = Field(default="", max_length=2000)
    credit_request_id: Optional[str] = None


class DocumentRequestSubmitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)


_STAFF_CREATOR_ROLES = {
    RoleType.RM, RoleType.PRODUCT_SPECIALIST, RoleType.CREDIT_SPECIALIST,
    RoleType.INSURANCE_SPECIALIST, RoleType.LEGAL_SPECIALIST,
}


@router.post("/cases/{case_id}/document-requests", status_code=status.HTTP_201_CREATED)
def create_document_request(
    case_id: str, body: DocumentRequestCreateBody,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    role = identity.roles[0]
    if role not in _STAFF_CREATOR_ROLES:
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Vai tro nay khong duoc tao yeu cau bo sung ho so.")
    stored = _repo().get_case(case_id)
    if stored is None:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Case khong ton tai.")
    state_value = stored.state
    if state_value.context.customer.customer_id not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Case ngoai pham vi khach hang duoc giao.")

    workflow = _workflow()
    doc_request = workflow.create_document_request(
        case_id=case_id, customer_id=state_value.context.customer.customer_id,
        created_by_role=role.value, created_by_id=identity.employee_id,
        document_type=body.document_type, title=body.title,
        customer_safe_reason=body.customer_safe_reason,
        internal_reason=body.internal_reason or None,
        credit_request_id=body.credit_request_id,
    )
    workflow.append_timeline_event(
        case_id=case_id, event_type="DOCUMENT_REQUEST_CREATED",
        actor_role=role.value, actor_id=identity.employee_id,
        title=body.title, entity_type="document_request", entity_id=doc_request["request_id"],
    )
    workflow.create_notification(
        recipient_id=state_value.context.customer.customer_id, recipient_role=RoleType.CUSTOMER_USER.value,
        case_id=case_id, type_="document_requested", title=body.title,
        message=body.customer_safe_reason, route="/customer/document-requests",
    )
    return doc_request


@router.get("/cases/{case_id}/document-requests")
def list_case_document_requests(
    case_id: str, identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    _case_access(case_id, identity)
    return _workflow().list_document_requests_for_case(case_id)


@router.get("/customer/document-requests")
def list_my_document_requests(
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    if identity.roles[0] != RoleType.CUSTOMER_USER:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_ROLE_REQUIRED", "Chi Customer duoc xem muc nay.")
    workflow = _workflow()
    results: List[Dict[str, Any]] = []
    for customer_id in identity.customer_scope:
        results.extend(workflow.list_document_requests_for_customer(customer_id))
    results.sort(key=lambda row: row["created_at"], reverse=True)
    return results


@router.get("/document-requests/{request_id}")
def get_document_request(
    request_id: str, identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    doc_request = _workflow().get_document_request(request_id)
    if not doc_request:
        raise _error(status.HTTP_404_NOT_FOUND, "DOCUMENT_REQUEST_NOT_FOUND", "Khong tim thay yeu cau bo sung ho so.")
    if doc_request["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen xem yeu cau nay.")
    return doc_request


@router.post("/document-requests/{request_id}/submit")
def submit_document_request(
    request_id: str, body: DocumentRequestSubmitBody,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    """Customer attaches an already-uploaded replacement document (via the
    existing POST /sales-cases/{case_id}/documents upload) to an open
    DocumentRequest. Uploading is intentionally not duplicated here -- it
    reuses the proven intake document pipeline (dedup, versioning, the old
    document preserved) rather than a second file-handling code path."""
    if identity.roles[0] != RoleType.CUSTOMER_USER:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_ROLE_REQUIRED", "Chi Customer duoc bo sung ho so.")
    doc_request = _workflow().get_document_request(request_id)
    if not doc_request:
        raise _error(status.HTTP_404_NOT_FOUND, "DOCUMENT_REQUEST_NOT_FOUND", "Khong tim thay yeu cau bo sung ho so.")
    if doc_request["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen thao tac yeu cau nay.")
    if doc_request["status"] not in {"REQUESTED", "PROCESSING"}:
        raise _error(status.HTTP_409_CONFLICT, "DOCUMENT_REQUEST_NOT_OPEN", "Yeu cau nay khong con cho bo sung.")

    repository = _repo()
    case_id = doc_request["case_id"]
    with repository._connect() as conn:
        intake_row = conn.execute("SELECT intake_id FROM intake_sessions WHERE case_id=?", (case_id,)).fetchone()
    if not intake_row:
        raise _error(status.HTTP_404_NOT_FOUND, "CASE_NOT_FOUND", "Khong tim thay ho so goc cua yeu cau nay.")
    known_ids = {doc.document_id for doc in repository.list_intake_documents(intake_row["intake_id"])}
    if body.document_id not in known_ids:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNKNOWN_DOCUMENT_ID",
                     "document_id chua duoc upload cho case nay. Hay upload truoc roi thu lai.")

    workflow = _workflow()
    updated = workflow.mark_document_submitted(request_id, replacement_document_id=body.document_id)
    workflow.append_timeline_event(
        case_id=case_id, event_type="CUSTOMER_DOCUMENT_RESUBMITTED",
        actor_role=RoleType.CUSTOMER_USER.value, actor_id=identity.employee_id,
        title="Khach hang da bo sung ho so", entity_type="document", entity_id=body.document_id,
        metadata={"document_request_id": request_id},
    )
    workflow.append_timeline_event(
        case_id=case_id, event_type="EVIDENCE_UPDATED",
        actor_role=RoleType.CUSTOMER_USER.value, actor_id=identity.employee_id,
        title="Ho so bang chung da duoc cap nhat", entity_type="document", entity_id=body.document_id,
    )

    credit_request_id = doc_request.get("credit_request_id")
    if credit_request_id:
        credit_row = _credit_repo.get(credit_request_id)
        if credit_row:
            # Resubmission puts the request straight back in the Credit
            # Specialist's queue (WithRM -> PendingAppraisal) -- no second
            # manual RM forward needed for every round; see
            # reopen_after_resubmission()'s docstring.
            reopened_row = _credit_repo.reopen_after_resubmission(credit_request_id)
            if reopened_row:
                credit_row = reopened_row
                workflow.append_timeline_event(
                    case_id=case_id, event_type="WORK_ITEM_REOPENED",
                    actor_role=RoleType.CUSTOMER_USER.value, actor_id=identity.employee_id,
                    title=f"Ho so tin dung {credit_request_id} duoc mo lai cho Credit Specialist sau khi khach hang bo sung",
                    entity_type="credit_request", entity_id=credit_request_id,
                )
            from app.storage.employee_db import create_work_item
            create_work_item(
                {
                    "item_id": f"CREDIT-NBW-{credit_request_id}-appraisal",
                    "employee_id": "SPEC-CREDIT-001",
                    "title": f"Xem xet lai - co ho so moi tu khach hang ({credit_request_id})",
                    "urgency": 0.85, "risk_severity": 0.5, "business_impact": 0.7,
                    "customer_commitment": 0.6, "dependency_unblock": 0.7, "ownership_match": 1.0,
                    "estimated_effort": 0.3, "dependency_ids": [],
                    "role_required": RoleType.CREDIT_SPECIALIST.value, "customer_id": credit_row["customer_id"],
                }
            )
            workflow.create_notification(
                recipient_id="SPEC-CREDIT-001", recipient_role=RoleType.CREDIT_SPECIALIST.value,
                case_id=case_id, type_="customer_resubmitted",
                title=f"Khach hang da bo sung ho so cho {credit_request_id}",
                message="Co ho so moi can xem xet lai.", route=f"/credit-requests/{credit_request_id}",
            )
            if credit_row.get("assigned_rm_id"):
                workflow.create_notification(
                    recipient_id=credit_row["assigned_rm_id"], recipient_role=RoleType.RM.value,
                    case_id=case_id, type_="customer_resubmitted",
                    title=f"Khach hang da bo sung ho so cho {credit_request_id}",
                    message="Chuyen vien tin dung se xem xet lai ho so.",
                    route=f"/credit-requests/{credit_request_id}",
                )
    return updated


@router.post("/document-requests/{request_id}/cancel")
def cancel_document_request(
    request_id: str, identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    role = identity.roles[0]
    doc_request = _workflow().get_document_request(request_id)
    if not doc_request:
        raise _error(status.HTTP_404_NOT_FOUND, "DOCUMENT_REQUEST_NOT_FOUND", "Khong tim thay yeu cau bo sung ho so.")
    is_customer_owner = role == RoleType.CUSTOMER_USER and doc_request["customer_id"] in identity.customer_scope
    is_staff_in_scope = role in _STAFF_CREATOR_ROLES and doc_request["customer_id"] in identity.customer_scope
    if not (is_customer_owner or is_staff_in_scope):
        raise _error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Khong co quyen huy yeu cau nay.")
    try:
        return _workflow().cancel_document_request(request_id)
    except ValueError as exc:
        raise _error(status.HTTP_409_CONFLICT, "DOCUMENT_REQUEST_NOT_OPEN", str(exc)) from exc


# --- Notifications -------------------------------------------------------------

@router.get("/me/notifications")
def list_my_notifications(
    unread_only: bool = Query(default=False),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    return _workflow().list_notifications(identity.employee_id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str, identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, bool]:
    success = _workflow().mark_notification_read(notification_id, recipient_id=identity.employee_id)
    return {"success": success}


# --- Dynamic specialist work-item queue (section 3: no static JS/seed-only queue) --

_SEED_ITEM_PREFIXES = ("TASK-",)

_TYPE_BY_ITEM_PREFIX = (
    ("FORWARD-", "specialist_review_assignment"),
    ("CREDIT-NBW-", "credit_appraisal"),
    ("REVIEW-NOTIFY-", "specialist_feedback"),
    ("TASK-", "demo_seed"),
)


def _work_item_type(item_id: str) -> str:
    for prefix, label in _TYPE_BY_ITEM_PREFIX:
        if item_id.startswith(prefix):
            return label
    return "general"


def _priority_label(urgency: float, risk_severity: float, customer_commitment: float) -> str:
    if urgency >= 0.8 or risk_severity >= 0.8:
        return "high"
    if customer_commitment >= 0.7 or urgency >= 0.6:
        return "medium"
    return "low"


def _resolve_case_id(item_id: str) -> Optional[str]:
    if item_id.startswith("FORWARD-"):
        # FORWARD-<case_id>-<role>-v<n>
        rest = item_id[len("FORWARD-"):]
        parts = rest.rsplit("-", 2)
        return parts[0] if len(parts) == 3 else None
    if item_id.startswith("REVIEW-NOTIFY-"):
        # REVIEW-NOTIFY-<case_id>-<version>-<event_type>-<employee>-<hash>
        rest = item_id[len("REVIEW-NOTIFY-"):]
        parts = rest.split("-")
        return parts[0] if parts else None
    return None


def _resolve_credit_request_id(item_id: str) -> Optional[str]:
    if item_id.startswith("CREDIT-NBW-"):
        rest = item_id[len("CREDIT-NBW-"):]
        # CREDIT-NBW-<request_id>-<suffix...>; request_id itself is "CR-XXXX"
        parts = rest.split("-")
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
    return None


@router.get("/work-items/my")
def get_my_dynamic_work_items(
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    """Real, DB-backed specialist queue -- every row comes from
    employee_work_items (a real SQLite table), never from a JavaScript
    fixture. Distinguishes genuinely-triggered rows (FORWARD-*, CREDIT-NBW-*,
    REVIEW-NOTIFY-*) from the static demo seed (TASK-*) via is_demo_seed
    rather than deleting the seed rows outright, since they still give a
    fresh demo database some baseline content to show before any real
    action has happened."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM employee_work_items WHERE employee_id = ? AND status != 'completed' "
            "ORDER BY created_at DESC",
            (identity.employee_id,),
        ).fetchall()
    finally:
        conn.close()

    repository = _repo()
    items: List[Dict[str, Any]] = []
    for row in rows:
        item_id = row["item_id"]
        case_id = _resolve_case_id(item_id)
        credit_request_id = _resolve_credit_request_id(item_id)
        company_name = None
        evidence_summary = "N/A"
        deep_link = None

        if credit_request_id:
            credit_row = _credit_repo.get(credit_request_id)
            if credit_row:
                company_name = credit_row.get("company_name")
                case_id = case_id or credit_row.get("case_id")
                deep_link = f"/credit-requests/{credit_request_id}"
        if case_id:
            stored = repository.get_case(case_id)
            if stored and stored.state.context.customer:
                company_name = company_name or stored.state.context.customer.customer_id
            deep_link = deep_link or f"/cases/{case_id}"
            try:
                evidence_summary = f"{len(stored.state.evidences)} evidence claim(s)" if stored else "N/A"
            except Exception:
                evidence_summary = "N/A"

        items.append(
            {
                "work_item_id": item_id,
                "case_id": case_id,
                "credit_request_id": credit_request_id,
                "company_name": company_name or row["customer_id"],
                "work_item_type": _work_item_type(item_id),
                "trigger_reason": row["title"],
                "priority": _priority_label(row["urgency"], row["risk_severity"], row["customer_commitment"]),
                "assigned_role": row["role_required"],
                "status": row["status"].upper(),
                "created_at": row["created_at"],
                "evidence_summary": evidence_summary,
                "deep_link": deep_link,
                "is_demo_seed": item_id.startswith(_SEED_ITEM_PREFIXES),
            }
        )
    return items
