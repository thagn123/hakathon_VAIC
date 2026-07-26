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
)
from app.schemas.v2.employee import RoleType, VerifiedIdentity
from app.storage.credit_request_repository import CreditRequestConflict, CreditRequestRepository
from app.storage.repository import V2Repository


router = APIRouter(prefix="/credit-requests", tags=["Corporate Credit Requests"])
_repo = CreditRequestRepository()
_appraiser = CreditReadinessService()
_events = JsonEventLogger(settings.AUDIT_LOG_PATH)


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
            if stored and stored.state and stored.state.customer:
                ai_profile = stored.state.customer.model_dump(mode="json")
                
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
    return row
