"""Customer form -> RM -> Credit Specialist appraisal -> Manager final decision."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.v2.employee_router import require_capability, require_verified_identity
from app.config import settings
from app.credit.service import CreditReadinessService
from app.integrations.enterprise import SQLiteCRMAdapter
from app.intake import IntakeService
from app.observability.runtime import JsonEventLogger
from app.schemas.v2.credit_request import (
    CreditAppraisalRequest,
    CorporateCreditRequestCreate,
    CreditDecisionRequest,
    CreditForwardRequest,
    CreditProposalRequest,
)
from app.schemas.v2.employee import RoleType, VerifiedIdentity
from app.storage.credit_request_repository import CreditRequestConflict, CreditRequestRepository
from app.storage.employee_db import create_work_item
from app.storage.repository import V2Repository
from app.storage.workflow_repository import WorkflowRepository


router = APIRouter(prefix="/credit-requests", tags=["Corporate Credit Requests"])
_repo = CreditRequestRepository()
_appraiser = CreditReadinessService()
_events = JsonEventLogger(settings.AUDIT_LOG_PATH)

_CREDIT_SPECIALIST_PERSONA = "SPEC-CREDIT-001"
_MANAGER_PERSONA = "MGR-HN-01"


def _workflow() -> WorkflowRepository:
    """Constructed fresh per call -- same rationale as _enrich_with_sales_case's
    V2Repository/IntakeService construction just above."""
    return WorkflowRepository(settings.V2_DB_PATH)


def _error(http_status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


_CIC_LABELS = {
    1: "Nhóm 1 (Nợ đủ tiêu chuẩn)",
    2: "Nhóm 2 (Nợ cần chú ý)",
    3: "Nhóm 3 (Nợ dưới tiêu chuẩn)",
    4: "Nhóm 4 (Nợ nghi ngờ)",
    5: "Nhóm 5 (Nợ có khả năng mất vốn)",
}


def _apply_bank_credit_records(
    body: CorporateCreditRequestCreate,
) -> tuple[CorporateCreditRequestCreate, Dict[str, Any]]:
    """Bank-side CIC/repayment data overrides the customer-typed values.

    The customer form keeps the fields as reference input, but when the bank
    already has credit_history records they are the source of truth.
    """
    records = SQLiteCRMAdapter().list_credit_history(body.customer_id)
    if not records:
        return body, {}

    worst_group = max(int(r["cic_group"]) for r in records)
    max_dpd = max(int(r["max_days_past_due_12m"]) for r in records)
    restructured = any(r["restructured"] for r in records)
    outstanding_billion = round(
        sum(float(r["outstanding_amount_vnd"]) for r in records) / 1_000_000_000, 2
    )
    overrides = {
        "cic_debt_classification": _CIC_LABELS.get(worst_group, f"Nhóm {worst_group}"),
        "repayment_history": "Có chậm trả" if (max_dpd > 10 or restructured) else "Hoàn hảo",
        "current_debt_billion_vnd": outstanding_billion,
    }
    return body.model_copy(update=overrides), overrides


def _can_view(row: Dict[str, Any], identity: VerifiedIdentity) -> bool:
    role = identity.roles[0]
    if role == RoleType.CUSTOMER_USER:
        return row["submitted_by"] == identity.employee_id
    if role in {RoleType.RM, RoleType.CREDIT_SPECIALIST, RoleType.MANAGER}:
        return row["customer_id"] in identity.customer_scope
    return False


def _customer_view(row: Dict[str, Any]) -> Dict[str, Any]:
    """Customer sees submitted form + public status, never internal AI/review data."""
    fields = {
        "request_id", "case_id", "customer_id", "company_name", "tax_id",
        "legal_type", "representative", "industry", "business_scale",
        "total_assets_billion_vnd", "net_revenue_billion_vnd",
        "net_profit_billion_vnd", "debt_to_equity_ratio",
        "cic_debt_classification", "current_debt_billion_vnd",
        "collateral_description", "collateral_value_billion_vnd",
        "casa_avg_balance_billion_vnd", "repayment_history", "request_type",
        "requested_amount_vnd", "requested_term_months", "purpose", "status",
        "final_decision", "submitted_at", "updated_at",
    }
    return {key: value for key, value in row.items() if key in fields}


def _to_create_payload(row: Dict[str, Any]) -> CorporateCreditRequestCreate:
    return CorporateCreditRequestCreate(
        customer_id=row["customer_id"],
        company_name=row["company_name"],
        tax_id=row["tax_id"],
        legal_type=row["legal_type"],
        representative=row["representative"],
        industry=row["industry"],
        business_scale=row["business_scale"],
        total_assets_billion_vnd=row["total_assets_billion_vnd"],
        net_revenue_billion_vnd=row["net_revenue_billion_vnd"],
        net_profit_billion_vnd=row["net_profit_billion_vnd"],
        debt_to_equity_ratio=row["debt_to_equity_ratio"],
        cic_debt_classification=row["cic_debt_classification"],
        current_debt_billion_vnd=row["current_debt_billion_vnd"],
        collateral_description=row["collateral_description"],
        collateral_value_billion_vnd=row["collateral_value_billion_vnd"],
        casa_avg_balance_billion_vnd=row["casa_avg_balance_billion_vnd"],
        repayment_history=row["repayment_history"],
        request_type=row["request_type"],
        requested_amount_vnd=row["requested_amount_vnd"],
        requested_term_months=row["requested_term_months"],
        purpose=row["purpose"],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_credit_request(
    body: CorporateCreditRequestCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    if identity.roles[0] != RoleType.CUSTOMER_USER:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_ROLE_REQUIRED", "Chỉ Customer User được gửi yêu cầu.")
    require_capability(identity, "case:create")
    if body.customer_id not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_SCOPE_DENIED", "Khách hàng nằm ngoài phạm vi tài khoản.")

    body, bank_overrides = _apply_bank_credit_records(body)
    service_advisory = _appraiser.recommend_services(body)
    row = _repo.create(
        body,
        submitted_by=identity.employee_id,
        idempotency_key=idempotency_key,
        service_advisory=service_advisory,
    )
    _events.emit(
        "credit_request_submitted",
        request_id=row["request_id"],
        case_id=row["case_id"],
        actor=identity.employee_id,
        service_count=len(service_advisory["services"]),
        bank_overridden_fields=sorted(bank_overrides.keys()),
    )
    if row.get("case_id"):
        _workflow().append_timeline_event(
            case_id=row["case_id"], event_type="CREDIT_REQUEST_SUBMITTED",
            actor_role=RoleType.CUSTOMER_USER.value, actor_id=identity.employee_id,
            title=f"Khach hang gui yeu cau tin dung {row['request_id']}",
            description=body.purpose, entity_type="credit_request", entity_id=row["request_id"],
        )
    return _customer_view(row)


def _enrich_with_sales_case(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # V2Repository/IntakeService are constructed fresh per call (never
    # module-level singletons) so settings.V2_DB_PATH is read live -- same
    # rationale as app/api/v2/router.py's repo()/intake_service() closures
    # and app/api/v2/employee_router.py's _repo(). Previously this imported
    # a `repo`/`intake_service` name from modules that never defined one at
    # module scope (both only exist as closures private to
    # router.py:create_router()), so this function raised ImportError on
    # every call -- GET /api/v2/credit-requests and GET
    # /api/v2/credit-requests/{id} 500'd unconditionally for every RM/Credit
    # Specialist/Manager caller.
    repository = V2Repository(settings.V2_DB_PATH)
    service = IntakeService(repository)
    
    enriched = []
    for row in rows:
        case_id = row.get("case_id")
        documents = []
        ai_profile = None
        if case_id:
            with repository._connect() as conn:
                intake_row = conn.execute("SELECT intake_id FROM intake_sessions WHERE case_id=?", (case_id,)).fetchone()
            if intake_row:
                intake_id = intake_row["intake_id"]
                docs = repository.list_intake_documents(intake_id)
                documents = [service.public_document(d) for d in docs]
            
            stored = repository.get_case(case_id)
            # SharedCaseState has no top-level `customer` field -- the
            # customer snapshot lives at state.context.customer. This was
            # dormant until a case actually completed run-analysis (only
            # then does get_case() return a non-None state), so it never
            # fired in any prior verified journey.
            if stored and stored.state and stored.state.context and stored.state.context.customer:
                ai_profile = stored.state.context.customer.model_dump(mode="json")
                
        row_copy = dict(row)
        row_copy["sales_case_documents"] = documents
        row_copy["sales_case_profile"] = ai_profile
        enriched.append(row_copy)
    return enriched


@router.get("", response_model=List[Dict[str, Any]])
def list_credit_requests(
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> List[Dict[str, Any]]:
    role = identity.roles[0]
    if role == RoleType.CUSTOMER_USER:
        require_capability(identity, "case:read")
        return [
            _customer_view(row)
            for row in _repo.list_for_actor(submitted_by=identity.employee_id)
        ]
    
    rows = []
    if role == RoleType.RM:
        require_capability(identity, "case:read")
        rows = _repo.list_for_actor(customer_scope=identity.customer_scope)
    elif role == RoleType.CREDIT_SPECIALIST:
        require_capability(identity, "case:read")
        rows = _repo.list_for_actor(customer_scope=identity.customer_scope)
    elif role == RoleType.MANAGER:
        require_capability(identity, "case:read")
        rows = _repo.list_for_actor(customer_scope=identity.customer_scope)
    else:
        raise _error(status.HTTP_403_FORBIDDEN, "CREDIT_REQUEST_ACCESS_DENIED", "Vai trò không được xem yêu cầu tín dụng.")
        
    return _enrich_with_sales_case(rows)


@router.get("/{request_id}", response_model=Dict[str, Any])
def get_credit_request(
    request_id: str,
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    row = _repo.get(request_id)
    if not row:
        raise _error(status.HTTP_404_NOT_FOUND, "CREDIT_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu.")
    if not _can_view(row, identity):
        raise _error(status.HTTP_403_FORBIDDEN, "CREDIT_REQUEST_ACCESS_DENIED", "Không có quyền xem yêu cầu.")
    if identity.roles[0] == RoleType.CUSTOMER_USER:
        return _customer_view(row)
    return _enrich_with_sales_case([row])[0]


@router.post("/{request_id}/forward", response_model=Dict[str, Any])
def forward_credit_request(
    request_id: str,
    body: CreditForwardRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    if identity.roles[0] != RoleType.RM:
        raise _error(status.HTTP_403_FORBIDDEN, "RM_ROLE_REQUIRED", "Chỉ RM được chuyển tờ trình lên phê duyệt.")
    require_capability(identity, "credit:forward")
    current = _repo.get(request_id)
    if not current:
        raise _error(status.HTTP_404_NOT_FOUND, "CREDIT_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu.")
    if current["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_SCOPE_DENIED", "Yêu cầu nằm ngoài phạm vi được giao.")

    try:
        row = _repo.forward(
            request_id,
            rm_id=identity.employee_id,
            rm_note=body.rm_note,
            idempotency_key=idempotency_key,
        )
    except CreditRequestConflict as exc:
        raise _error(status.HTTP_409_CONFLICT, "CREDIT_REQUEST_CONFLICT", str(exc)) from exc

    _events.emit(
        "credit_request_forwarded",
        request_id=request_id,
        case_id=row["case_id"],
        actor=identity.employee_id,
        service_count=len(row.get("service_recommendation") or []),
    )

    item_id = f"CREDIT-NBW-{request_id}-appraisal"
    create_work_item(
        {
            "item_id": item_id, "employee_id": _CREDIT_SPECIALIST_PERSONA,
            "title": f"Tham dinh ho so tin dung {row['company_name']} ({request_id})",
            "urgency": 0.8, "risk_severity": 0.6, "business_impact": 0.7,
            "customer_commitment": 0.5, "dependency_unblock": 0.6, "ownership_match": 1.0,
            "estimated_effort": 0.4, "dependency_ids": [],
            "role_required": RoleType.CREDIT_SPECIALIST.value, "customer_id": row["customer_id"],
        }
    )
    workflow = _workflow()
    if row.get("case_id"):
        workflow.append_timeline_event(
            case_id=row["case_id"], event_type="WORK_ITEM_CREATED",
            actor_role=RoleType.RM.value, actor_id=identity.employee_id,
            title=f"RM chuyen yeu cau tin dung {request_id} cho Credit Specialist",
            description=body.rm_note, entity_type="work_item", entity_id=item_id,
        )
    workflow.create_notification(
        recipient_id=_CREDIT_SPECIALIST_PERSONA, recipient_role=RoleType.CREDIT_SPECIALIST.value,
        case_id=row.get("case_id"), type_="credit_request_forwarded",
        title=f"Yeu cau tin dung {request_id} can tham dinh",
        message=f"RM {identity.employee_id} da chuyen ho so {row['company_name']} cho ban tham dinh.",
        route=f"/credit-requests/{request_id}",
    )
    return row


@router.post("/{request_id}/appraisal", response_model=Dict[str, Any])
def appraise_credit_request(
    request_id: str,
    body: CreditAppraisalRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    if identity.roles[0] != RoleType.CREDIT_SPECIALIST:
        raise _error(status.HTTP_403_FORBIDDEN, "CREDIT_SPECIALIST_REQUIRED", "Chỉ Credit Specialist được thẩm định.")
    require_capability(identity, "credit:appraise")
    current = _repo.get(request_id)
    if not current:
        raise _error(status.HTTP_404_NOT_FOUND, "CREDIT_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu.")
    if current["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_SCOPE_DENIED", "Yêu cầu nằm ngoài phạm vi được giao.")

    agent_appraisal = None
    if body.recommendation != "needs_more_information":
        agent_appraisal = _appraiser.appraise_request(_to_create_payload(current))
    try:
        row = _repo.appraise(
            request_id,
            expert_id=identity.employee_id,
            specialist_recommendation=body.recommendation,
            specialist_reason=body.reason,
            agent_appraisal=agent_appraisal,
            idempotency_key=idempotency_key,
        )
    except CreditRequestConflict as exc:
        raise _error(status.HTTP_409_CONFLICT, "CREDIT_REQUEST_CONFLICT", str(exc)) from exc
    _events.emit(
        "credit_request_appraised",
        request_id=request_id,
        case_id=row["case_id"],
        actor=identity.employee_id,
        specialist_recommendation=body.recommendation,
        agent_disbursement_recommendation=(
            agent_appraisal["recommendation"] if agent_appraisal else None
        ),
    )

    workflow = _workflow()
    case_id = row.get("case_id")
    prior_rounds = workflow.list_review_rounds(request_id)
    is_reopen = len(prior_rounds) > 0

    # A round-2+ appraisal resolves whichever DocumentRequest sent the
    # customer back in the first place -- the specialist is reviewing the
    # replacement evidence right now, so that request is no longer "open".
    resolved_document_request_id = None
    if is_reopen:
        # WORK_ITEM_REOPENED already fires at the actual reopen moment --
        # the customer's resubmission (see workflow_router.py's
        # submit_document_request -> reopen_after_resubmission()). Here we
        # only need to close out the document request this appraisal is
        # resolving.
        open_request = workflow.latest_open_document_request_for_credit_request(request_id)
        if open_request:
            resolved_document_request_id = open_request["request_id"]
            try:
                workflow.mark_document_resolved(open_request["request_id"], status="VERIFIED")
            except ValueError:
                pass

    workflow.create_review_round(
        request_id=request_id, case_id=case_id, specialist_id=identity.employee_id,
        recommendation=body.recommendation, specialist_reason=body.reason,
        appraisal_summary=agent_appraisal["summary"] if agent_appraisal else None,
        appraisal_score=agent_appraisal["score"] if agent_appraisal else None,
        agent_recommendation=agent_appraisal["recommendation"] if agent_appraisal else None,
        document_request_id=resolved_document_request_id,
    )
    if case_id:
        workflow.append_timeline_event(
            case_id=case_id, event_type="SPECIALIST_REVIEW_SUBMITTED",
            actor_role=RoleType.CREDIT_SPECIALIST.value, actor_id=identity.employee_id,
            title=f"Credit Specialist ghi nhan '{body.recommendation}' cho {request_id}",
            description=body.reason, entity_type="credit_request", entity_id=request_id,
        )

    if body.recommendation == "needs_more_information":
        doc_request = workflow.create_document_request(
            case_id=case_id or f"CR-{request_id}", customer_id=row["customer_id"],
            created_by_role=RoleType.CREDIT_SPECIALIST.value, created_by_id=identity.employee_id,
            document_type=body.requested_document_type,
            title="Bo sung ho so theo yeu cau Chuyen vien tin dung",
            customer_safe_reason=(
                "Chuyen vien tham dinh tin dung can quy khach bo sung ho so de tiep tuc xu ly "
                "yeu cau tin dung. Vui long tai len tai lieu thay the."
            ),
            internal_reason=body.reason, credit_request_id=request_id,
        )
        if case_id:
            workflow.append_timeline_event(
                case_id=case_id, event_type="DOCUMENT_REQUEST_CREATED",
                actor_role=RoleType.CREDIT_SPECIALIST.value, actor_id=identity.employee_id,
                title="Yeu cau khach hang bo sung ho so", entity_type="document_request",
                entity_id=doc_request["request_id"],
            )
        workflow.create_notification(
            recipient_id=row["submitted_by"], recipient_role=RoleType.CUSTOMER_USER.value,
            case_id=case_id, type_="document_requested",
            title="Can bo sung ho so tin dung",
            message=doc_request["customer_safe_reason"], route="/customer/document-requests",
        )
        if row.get("assigned_rm_id"):
            create_work_item(
                {
                    "item_id": f"CREDIT-NBW-{request_id}-waiting-customer",
                    "employee_id": row["assigned_rm_id"],
                    "title": f"Theo doi BCTC moi tu khach hang - {row['company_name']} ({request_id})",
                    "urgency": 0.7, "risk_severity": 0.4, "business_impact": 0.6,
                    "customer_commitment": 0.4, "dependency_unblock": 0.5, "ownership_match": 1.0,
                    "estimated_effort": 0.2, "dependency_ids": [],
                    "role_required": RoleType.RM.value, "customer_id": row["customer_id"],
                }
            )
            workflow.create_notification(
                recipient_id=row["assigned_rm_id"], recipient_role=RoleType.RM.value,
                case_id=case_id, type_="specialist_needs_more_information",
                title=f"Yeu cau tin dung {request_id} can bo sung ho so",
                message=body.reason, route=f"/credit-requests/{request_id}",
            )
    else:
        if case_id:
            workflow.append_timeline_event(
                case_id=case_id, event_type="SPECIALIST_REVIEW_CLEARED",
                actor_role=RoleType.CREDIT_SPECIALIST.value, actor_id=identity.employee_id,
                title=f"Credit Specialist hoan tat tham dinh {request_id} -- san sang tao proposal",
                entity_type="credit_request", entity_id=request_id,
            )
        if row.get("assigned_rm_id"):
            create_work_item(
                {
                    "item_id": f"CREDIT-NBW-{request_id}-ready-for-proposal",
                    "employee_id": row["assigned_rm_id"],
                    "title": f"Tao proposal cho ho so {row['company_name']} ({request_id})",
                    "urgency": 0.75, "risk_severity": 0.3, "business_impact": 0.7,
                    "customer_commitment": 0.5, "dependency_unblock": 0.6, "ownership_match": 1.0,
                    "estimated_effort": 0.2, "dependency_ids": [],
                    "role_required": RoleType.RM.value, "customer_id": row["customer_id"],
                }
            )
            workflow.create_notification(
                recipient_id=row["assigned_rm_id"], recipient_role=RoleType.RM.value,
                case_id=case_id, type_="specialist_cleared",
                title=f"Yeu cau tin dung {request_id} da duoc tham dinh xong",
                message=f"Chuyen vien khuyen nghi '{body.recommendation}'. San sang tao proposal.",
                route=f"/credit-requests/{request_id}",
            )
    return row


@router.post("/{request_id}/proposal", response_model=Dict[str, Any])
def create_credit_proposal(
    request_id: str,
    body: CreditProposalRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    """The real, gated step between a Credit Specialist clearing an
    appraisal and a Manager's final decision -- decide_credit_request below
    refuses to act until this has happened (proposal_created_at set)."""
    if identity.roles[0] != RoleType.RM:
        raise _error(status.HTTP_403_FORBIDDEN, "RM_ROLE_REQUIRED", "Chi RM duoc tao proposal.")
    require_capability(identity, "credit:create_proposal")
    current = _repo.get(request_id)
    if not current:
        raise _error(status.HTTP_404_NOT_FOUND, "CREDIT_REQUEST_NOT_FOUND", "Khong tim thay yeu cau.")
    if current["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_SCOPE_DENIED", "Yeu cau nam ngoai pham vi duoc giao.")

    try:
        row = _repo.create_proposal(
            request_id, rm_id=identity.employee_id, note=body.note, idempotency_key=idempotency_key,
        )
    except CreditRequestConflict as exc:
        raise _error(status.HTTP_409_CONFLICT, "CREDIT_REQUEST_CONFLICT", str(exc)) from exc

    _events.emit(
        "credit_request_proposal_created", request_id=request_id, case_id=row.get("case_id"),
        actor=identity.employee_id,
    )
    workflow = _workflow()
    if row.get("case_id"):
        workflow.append_timeline_event(
            case_id=row["case_id"], event_type="PROPOSAL_CREATED",
            actor_role=RoleType.RM.value, actor_id=identity.employee_id,
            title=f"RM tao proposal cho yeu cau tin dung {request_id}",
            description=body.note, entity_type="credit_request", entity_id=request_id,
        )
    workflow.create_notification(
        recipient_id=_MANAGER_PERSONA, recipient_role=RoleType.MANAGER.value,
        case_id=row.get("case_id"), type_="proposal_ready",
        title=f"Proposal {request_id} can phe duyet",
        message=f"RM {identity.employee_id} da tao proposal cho {row['company_name']}.",
        route=f"/credit-requests/{request_id}",
    )
    return row


@router.post("/{request_id}/decision", response_model=Dict[str, Any])
def decide_credit_request(
    request_id: str,
    body: CreditDecisionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    identity: VerifiedIdentity = Depends(require_verified_identity),
) -> Dict[str, Any]:
    if identity.roles[0] != RoleType.MANAGER:
        raise _error(status.HTTP_403_FORBIDDEN, "MANAGER_REQUIRED", "Chỉ Manager được phê duyệt cuối.")
    require_capability(identity, "credit:final_approve")
    current = _repo.get(request_id)
    if not current:
        raise _error(status.HTTP_404_NOT_FOUND, "CREDIT_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu.")
    if current["customer_id"] not in identity.customer_scope:
        raise _error(status.HTTP_403_FORBIDDEN, "CUSTOMER_SCOPE_DENIED", "Yêu cầu nằm ngoài phạm vi được giao.")

    try:
        row = _repo.decide(
            request_id,
            expert_id=identity.employee_id,
            decision=body.decision,
            reason=body.reason,
            idempotency_key=idempotency_key,
        )
    except CreditRequestConflict as exc:
        raise _error(status.HTTP_409_CONFLICT, "CREDIT_REQUEST_CONFLICT", str(exc)) from exc

    _events.emit(
        "credit_request_final_decision",
        request_id=request_id,
        case_id=row["case_id"],
        actor=identity.employee_id,
        decision=body.decision,
    )

    workflow = _workflow()
    case_id = row.get("case_id")
    is_terminal = body.decision in {"approved", "rejected"}
    if case_id:
        workflow.append_timeline_event(
            case_id=case_id, event_type="APPROVAL_SUBMITTED",
            actor_role=RoleType.MANAGER.value, actor_id=identity.employee_id,
            title=f"Manager ghi nhan quyet dinh '{body.decision}' cho {request_id}",
            description=body.reason, entity_type="credit_request", entity_id=request_id,
        )
        if is_terminal:
            workflow.append_timeline_event(
                case_id=case_id, event_type="APPROVAL_COMPLETED",
                actor_role=RoleType.MANAGER.value, actor_id=identity.employee_id,
                title=f"Yeu cau tin dung {request_id} da duoc {body.decision}",
                entity_type="credit_request", entity_id=request_id,
            )
    if row.get("assigned_rm_id"):
        workflow.create_notification(
            recipient_id=row["assigned_rm_id"], recipient_role=RoleType.RM.value,
            case_id=case_id, type_="manager_decision",
            title=f"Manager da quyet dinh yeu cau tin dung {request_id}",
            message=f"Quyet dinh: {body.decision}. Ly do: {body.reason}",
            route=f"/credit-requests/{request_id}",
        )
        if not is_terminal:
            create_work_item(
                {
                    "item_id": f"CREDIT-NBW-{request_id}-appraisal",
                    "employee_id": _CREDIT_SPECIALIST_PERSONA,
                    "title": f"Manager yeu cau xem xet lai ho so {row['company_name']} ({request_id})",
                    "urgency": 0.85, "risk_severity": 0.6, "business_impact": 0.7,
                    "customer_commitment": 0.5, "dependency_unblock": 0.6, "ownership_match": 1.0,
                    "estimated_effort": 0.4, "dependency_ids": [],
                    "role_required": RoleType.CREDIT_SPECIALIST.value, "customer_id": row["customer_id"],
                }
            )
    return row
