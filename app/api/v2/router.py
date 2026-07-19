"""Typed V2 API for the complete synthetic RM journey."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from app.actions.executor import ActionExecutorV2, ExecutionDenied
from app.auth import verify_session_token
from app.approval.service import ApprovalError, ApprovalServiceV2, payload_hash
from app.config import settings
from app.context.assembler import ContextAssembler
from app.context.conversation_state import ConversationStateService, ConversationStateStore
from app.context.customer_service import CustomerContextService
from app.context.employee_service import EmployeeContextService
from app.context.workspace_service import WorkspaceContextService, WorkspaceSessionStore
from app.integrations.enterprise import (
    SQLiteCRMAdapter,
    SQLiteIAMAdapter,
    SQLiteSSOAdapter,
    map_enterprise_role_to_role_type,
)
from app.integrations.pg import (
    PostgresCRMAdapter,
    PostgresIAMAdapter,
    PostgresSSOAdapter,
)
from app.integrations.errors import ContextAccessDeniedError, ContextError, UpstreamTimeoutError, UpstreamUnavailableError
from app.integrations.resilient import ResilientCRMAdapter


def _sso_adapter():
    """CRM/IAM/SSO come from PostgreSQL when DATABASE_URL is set (pilot/prod),
    else the local SQLite mirror (dev). Same ports, so callers are unchanged."""
    return PostgresSSOAdapter() if settings.DATABASE_URL else SQLiteSSOAdapter()


def _iam_adapter():
    return PostgresIAMAdapter() if settings.DATABASE_URL else SQLiteIAMAdapter()


def _crm_adapter():
    return PostgresCRMAdapter() if settings.DATABASE_URL else SQLiteCRMAdapter()
from app.intake import IntakeService, IntakeValidationError
from app.knowledge.service import DEFAULT_PRODUCTS, DEFAULT_SOURCE_CARD as PRODUCT_SOURCE_CARD, ProductKnowledgeService
from app.knowledge.legal_service import DEFAULT_SOURCE_CARD as LEGAL_SOURCE_CARD, LegalKnowledgeService
from app.knowledge.parsers import UnsupportedDocumentError, extraction_quality, parse_document_bytes
from app.knowledge.upload_ingestion import GovernedUploadIngestionService
from app.observability.runtime import JsonEventLogger, metrics
from app.schemas.v2.context_snapshot import ContextSnapshot, WorkspaceDocument
from app.schemas.v2.common import ResolvedValue, SourceType
from app.schemas.v2.intake import DocumentJobStatus, IntakeStatus, ProfileChange
from app.schemas.v2.shared_case_state import (
    Approval, ApprovalStatus, CaseStatus, Request, SharedCaseState, Workflow,
)
from app.safety.input_guardrails_v2 import screen_input
from app.storage.repository import StateConflictError, StoredCase, StoredIntake, V2Repository
from app.workflow.engine import V2WorkflowEngine
from app.workflow.impact import CONTEXT_CORRECTION_POLICIES


class CreateCaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class ResolveContextBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Optional[str] = None
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class MessageBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    mode: Literal["append", "replace"] = "append"
    expected_state_version: int = Field(ge=1)


class DocumentsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: List[Dict[str, Any]] = Field(min_length=1)
    expected_state_version: int = Field(ge=1)


class ContextCorrectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    new_value: Any
    reason: str = Field(min_length=3)
    expected_state_version: int = Field(ge=1)


class ResumeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: List[Dict[str, Any]] = Field(default_factory=list)
    changes: List[str] = Field(default_factory=list)
    expected_state_version: int = Field(ge=1)


class ApproveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_state_version: int = Field(ge=1)


class ExecuteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=6)
    expected_state_version: int = Field(ge=1)


class RejectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3)
    expected_state_version: int = Field(ge=1)


class CreateSalesCaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=2)
    tax_code: Optional[str] = None
    industry: Optional[str] = None
    contact: Optional[str] = None
    employees_count: Optional[int] = Field(default=None, ge=1)
    annual_revenue: Optional[float] = Field(default=None, ge=0)
    operating_years: Optional[int] = Field(default=None, ge=0)
    requested_amount_vnd: Optional[float] = Field(default=None, ge=0)
    preferred_timeline: Optional[str] = None
    need_text: str = Field(min_length=3)
    rm_note: Optional[str] = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    current_products: List[str] = Field(default_factory=list)


def _intake_assistance(context: ContextSnapshot) -> Dict[str, Any]:
    """Separate database inheritance, product advice, and credit verification."""
    attributes = context.customer.attributes
    employees = attributes.get("employees_count")
    accounts = attributes.get("account_or_unit_count")
    revenue = attributes.get("annual_revenue")
    years = attributes.get("operating_years")
    database_fields = {
        "companyName": attributes.get("name"),
        "taxCode": attributes.get("tax_code"),
        "industry": attributes.get("industry"),
    }

    eligible_ids = set()
    reasons = {}
    if employees and employees >= 10:
        eligible_ids.add("PROD-PAYROLL")
        reasons["PROD-PAYROLL"] = f"CRM ghi nhận {employees} nhân sự."
    if revenue and revenue >= 50_000_000_000 and accounts and accounts >= 3:
        eligible_ids.add("PROD-CASH-MGMT")
        reasons["PROD-CASH-MGMT"] = f"Doanh thu {float(revenue):,.0f} VND và {accounts} tài khoản/đơn vị."
    if years and years >= 2 and attributes.get("has_bad_debt_12m") is False:
        eligible_ids.add("PROD-WORKING-CAPITAL")
        reasons["PROD-WORKING-CAPITAL"] = (
            f"Hoạt động {years} năm và CRM chưa ghi nhận nợ xấu 12 tháng; "
            "vẫn cần Credit Agent xác minh hồ sơ."
        )
    catalog = json.loads(DEFAULT_PRODUCTS.read_text(encoding="utf-8"))["products"]
    products = [
        {
            "product_id": item["product_id"],
            "name": item["name"],
            "family": item["family"],
            "reason": reasons[item["product_id"]],
            "eligibility_summary": item["eligibility_summary"],
            "requires_credit_verification": item["family"] == "credit",
        }
        for item in catalog
        if item.get("active") and item["product_id"] in eligible_ids
    ]

    positives = []
    if attributes.get("has_bad_debt_12m") is False:
        positives.append("CRM chưa ghi nhận nợ xấu trong 12 tháng.")
    if years:
        positives.append(f"Doanh nghiệp hoạt động {years} năm.")
    missing = ["báo cáo tài chính đã xác minh", "dòng tiền trả nợ"]
    ubo_status = str(attributes.get("ubo_status", "")).lower()
    if not ubo_status or "chưa" in ubo_status or "not verified" in ubo_status:
        missing.append("xác minh UBO")

    # Cross-check khai báo CRM với credit_history (CIC mock trong SQLite).
    cic_records = SQLiteCRMAdapter().list_credit_history(context.customer.customer_id)
    worst_group = max((int(r["cic_group"]) for r in cic_records), default=None)
    max_dpd = max((int(r["max_days_past_due_12m"]) for r in cic_records), default=0)
    restructured = any(r["restructured"] for r in cic_records)
    if worst_group is None:
        status = "needs_verification"
        conclusion = "Chưa có bản ghi CIC; chưa đủ dữ liệu để kết luận chất lượng tín dụng."
        missing.insert(0, "CIC cập nhật")
    elif worst_group >= 3 or restructured:
        status = "warning"
        conclusion = (
            f"CIC ghi nhận nợ Nhóm {worst_group}"
            + (", đã cơ cấu lại thời hạn trả nợ" if restructured else "")
            + f"; chậm trả tối đa {max_dpd} ngày trong 12 tháng. Cần thẩm định kỹ trước khi đề xuất tín dụng."
        )
    elif worst_group == 2:
        status = "caution"
        conclusion = (
            f"CIC Nhóm 2 (nợ cần chú ý), chậm trả tối đa {max_dpd} ngày trong 12 tháng; "
            "có thể xem xét nhưng cần điều kiện bổ sung."
        )
    else:
        status = "clear"
        conclusion = f"CIC Nhóm 1 trên {len(cic_records)} khoản, không chậm trả đáng kể trong 12 tháng."
        positives.append(f"CIC: {len(cic_records)} khoản tín dụng, toàn bộ Nhóm 1.")

    return {
        "database_fields": {key: value for key, value in database_fields.items() if value},
        "product_suggestions": products,
        "credit_assessment": {
            "status": status,
            "conclusion": conclusion,
            "worst_cic_group": worst_group,
            "cic_record_count": len(cic_records),
            "positive_signals": positives,
            "missing_evidence": missing,
        },
        "source": "CRM context + credit_history (CIC mock) + danh mục sản phẩm ngân hàng",
        "requires_human_review": True,
    }


class ProfilePatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    changes: List[ProfileChange] = Field(min_length=1)


class ConfirmProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    attestation: bool


class RunAnalysisBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


class SalesApproveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_state_version: int = Field(ge=1)
    payload_hash: Optional[str] = None


def _default_assembler() -> ContextAssembler:
    sessions = WorkspaceSessionStore()
    sessions.set_session(
        "SESS-ABC", current_screen="customer_detail", selected_customer_id="COMP-ABC",
        active_case_id=None, active_task_id=None, selected_product_ids=[],
    )
    sessions.set_session(
        "SESS-XYZ", current_screen="customer_detail", selected_customer_id="COMP-XYZ",
        active_case_id=None, active_task_id=None, selected_product_ids=[],
    )
    sessions.set_session(
        "SESS-MP", current_screen="sales_intake", selected_customer_id="COMP-MP",
        active_case_id=None, active_task_id=None, selected_product_ids=[],
    )
    return ContextAssembler(
        EmployeeContextService(_sso_adapter(), _iam_adapter()),
        WorkspaceContextService(sessions),
        CustomerContextService(ResilientCRMAdapter(_crm_adapter())),
        ConversationStateService(ConversationStateStore()),
    )


def enforce_token_identity(
    authorization: Optional[str] = Header(None),
    x_employee_id: Optional[str] = Header(None),
) -> None:
    """Fail-closed guard for every /api/v2 route in this router.

    LOGIC: Đầu tiên đọc token đăng nhập; token nói "bạn là ai" thì header
    X-Employee-ID phải đúng là người đó, nên không ai mượn header để xem
    dữ liệu của người khác. Không có token thì chỉ cho qua ở chế độ demo.
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        payload = verify_session_token(token)
        if payload is not None:
            if x_employee_id and x_employee_id != payload["sub"]:
                metrics.increment("security.identity_header_mismatch")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "IDENTITY_MISMATCH", "message": "X-Employee-ID khong khop voi phien dang nhap."},
                )
            return
        if token.startswith("shb."):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHENTICATED", "message": "Phien dang nhap khong hop le hoac da het han."},
            )
        return
    if not settings.DEMO_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Thieu token dang nhap."},
        )


def create_router(
    *,
    repository: V2Repository | None = None,
    engine: V2WorkflowEngine | None = None,
    assembler: ContextAssembler | None = None,
    event_logger: JsonEventLogger | None = None,
) -> APIRouter:
    def repo() -> V2Repository:
        """Constructed fresh on every call (unless an explicit `repository`
        was injected into create_router(), which always wins outright) so
        settings.V2_DB_PATH is read live -- mirrors
        app/storage/employee_db.py's get_db_connection() and
        app/api/v2/employee_router.py's _repo(). The previous version built
        a single V2Repository once at create_router()-call time (i.e. once
        per process, at module import: `router = create_router()` at the
        bottom of this file), so any monkeypatch.setattr(settings,
        "V2_DB_PATH", ...) a test performed afterward was silently ignored
        for every /api/v2/cases and /api/v2/sales-cases endpoint -- a test
        using an isolated DB would see CASE_NOT_FOUND for a case it just
        wrote, or worse, would write into the real data/state/v2.sqlite3
        the live demo app reads. See
        docs/SPECIALIST_REVIEW_IMPLEMENTATION_REPORT.md sections 8/11.5."""
        return repository or V2Repository(settings.V2_DB_PATH)

    workflow = engine or V2WorkflowEngine()
    context_assembler = assembler or _default_assembler()
    logger = event_logger or JsonEventLogger(settings.AUDIT_LOG_PATH)

    def approval_service() -> ApprovalServiceV2:
        return ApprovalServiceV2(repo())

    def executor_service() -> ActionExecutorV2:
        return ActionExecutorV2(repo(), approval_service())

    def intake_service() -> IntakeService:
        return IntakeService(repo())

    router = APIRouter(prefix="/api/v2", tags=["v2"])

    def assemble(employee_id: str, session_id: str, documents=(), trace_id: str | None = None) -> ContextSnapshot:
        correlation = trace_id or f"TRACE-{uuid.uuid4().hex.upper()}"
        try:
            return context_assembler.assemble(
                employee_id=employee_id,
                session_id=session_id,
                documents=documents,
                correlation_id=correlation,
            )
        except ContextAccessDeniedError as exc:
            raise HTTPException(status_code=403, detail={"code": "CONTEXT_ACCESS_DENIED", "message": str(exc)}) from exc
        except ContextError as exc:
            raise HTTPException(status_code=503, detail={"code": "CONTEXT_UNAVAILABLE", "message": str(exc)}) from exc

    def owned(case_id: str, employee_id: str) -> StoredCase:
        stored = repo().get_case(case_id)
        if stored is None:
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND"})
        if not can_access_customer_case(
            owner_id=stored.state.context.employee.employee_id,
            customer_id=stored.state.context.customer.customer_id,
            employee_id=employee_id,
        ):
            metrics.increment("security.case_scope_denied")
            raise HTTPException(status_code=403, detail={"code": "CASE_ACCESS_DENIED"})
        return stored

    def intake_owned(case_id: str, employee_id: str) -> StoredIntake:
        stored = repo().get_intake(case_id)
        if stored is None:
            raise HTTPException(status_code=404, detail={"code": "SALES_CASE_NOT_FOUND"})
        if not can_access_customer_case(
            owner_id=stored.session.employee_id,
            customer_id=stored.session.customer_id,
            employee_id=employee_id,
        ):
            metrics.increment("security.intake_scope_denied")
            raise HTTPException(status_code=403, detail={"code": "CASE_ACCESS_DENIED"})
        return stored

    def actor_role(employee_id: str) -> str:
        correlation_id = f"TRACE-{uuid.uuid4().hex.upper()}"
        try:
            identity = _sso_adapter().get_employee_identity(employee_id, correlation_id=correlation_id)
        except ContextError as exc:
            raise HTTPException(status_code=503, detail={"code": "IAM_UNAVAILABLE"}) from exc
        return map_enterprise_role_to_role_type(identity["role"], identity["organization_unit"])

    def can_access_customer_case(*, owner_id: str, customer_id: Optional[str], employee_id: str) -> bool:
        if owner_id == employee_id:
            return True
        # Cross-owner access is deliberately one-way: an assigned RM may
        # receive customer-submitted data, but a Customer User can never
        # inspect an RM-owned analysis, internal notes or approval payload.
        if actor_role(employee_id) != "relationship_manager" or not customer_id:
            return False
        grant = iam_grant(employee_id)
        scope = set(grant.get("access_scope", {}).get("managed_customer_ids", []))
        return customer_id in scope and "case:read" in set(grant.get("permissions", []))

    def require_permission(employee_id: str, permission: str) -> Dict[str, Any]:
        grant = iam_grant(employee_id)
        permissions = set(grant["permissions"])
        compatible = {
            "case:create": "case:write",
            "case:confirm": "case:write",
            "case:run": "case:write",
            "case:approve": "approval:request",
            "case:execute": "approval:request",
            "case:audit": "case:read",
        }
        if actor_role(employee_id) == "customer_user" and permission in {
            "case:confirm", "case:run", "case:approve", "case:execute", "case:audit"
        }:
            accepted = {permission}
        else:
            accepted = {permission, compatible.get(permission, permission)}
        if not permissions.intersection(accepted):
            raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "permission": permission})
        return grant

    @staticmethod
    def intake_payload(stored: StoredIntake) -> Dict[str, Any]:
        session = stored.session
        return {
            "case_id": session.case_id,
            "intake_id": session.intake_id,
            "intake_status": session.status.value,
            "version": stored.version,
            "customer_id": session.customer_id,
            "manual_input": session.manual_input,
            "profile": session.profile.model_dump(mode="json") if session.profile else None,
            "conflicts": [item.model_dump(mode="json") for item in session.conflicts],
            "next_step": {
                "draft": "upload_documents",
                "files_uploaded": "process_documents",
                "document_processing": "wait_processing",
                "extraction_completed": "review_profile",
                "profile_review_required": "review_and_confirm",
                "profile_confirmed": "run_analysis",
                "processing_failed": "review_document_errors",
            }.get(session.status.value, "review"),
        }

    @staticmethod
    def intake_error(exc: IntakeValidationError) -> HTTPException:
        return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)})

    def persist(state_value: SharedCaseState, expected_version: Optional[int] = None) -> StoredCase:
        try:
            return repo().save_case(state_value, expected_version=expected_version)
        except StateConflictError as exc:
            metrics.increment("api.optimistic_conflict")
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT", "message": str(exc)}) from exc

    def response_payload(stored: StoredCase) -> Dict[str, Any]:
        return {"state_version": stored.version, "case": stored.state.model_dump(mode="json")}

    @staticmethod
    def action_payload(state_value: SharedCaseState) -> Dict[str, Any]:
        operations = state_value.operations_result or {}
        return operations.get("action_payload") or operations.get("crm_case_draft") or {}

    def iam_grant(employee_id: str) -> Dict[str, Any]:
        correlation_id = f"TRACE-{uuid.uuid4().hex.upper()}"
        try:
            return _iam_adapter().get_permissions(employee_id, correlation_id=correlation_id)
        except ContextError as exc:
            raise HTTPException(status_code=503, detail={"code": "IAM_UNAVAILABLE"}) from exc

    def merge_documents(
        existing: List[WorkspaceDocument],
        incoming: List[Dict[str, Any]],
    ) -> tuple[List[WorkspaceDocument], List[str]]:
        by_key = {(item.document_id, item.version): item for item in existing}
        changes: List[str] = []
        for raw in incoming:
            item = WorkspaceDocument.model_validate(raw)
            key = (item.document_id, item.version)
            if key not in by_key or by_key[key] != item:
                changes.append(f"document:{item.document_type}")
            by_key[key] = item
        return list(by_key.values()), list(dict.fromkeys(changes))

    @router.get("/context/current")
    def current_context(
        response: Response,
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
    ) -> Dict[str, Any]:
        trace_id = f"TRACE-{uuid.uuid4().hex.upper()}"
        response.headers["X-Trace-ID"] = trace_id
        context = assemble(x_employee_id, x_session_id, trace_id=trace_id)
        metrics.increment("context.loaded")
        return {"trace_id": trace_id, "context": context.model_dump(mode="json")}

    @router.post("/context/resolve")
    def resolve_context(
        body: ResolveContextBody,
        response: Response,
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
    ) -> Dict[str, Any]:
        trace_id = f"TRACE-{uuid.uuid4().hex.upper()}"
        safety = screen_input(body.message or "") if body.message else None
        if safety is not None and not safety.safe:
            metrics.increment("safety.prompt_injection_blocked")
            raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "flags": safety.flags})
        context = assemble(x_employee_id, x_session_id, body.documents, trace_id)
        response.headers["X-Trace-ID"] = trace_id
        metrics.increment("context.resolved")
        return {
            "trace_id": trace_id,
            "sanitized_message": safety.sanitized_text if safety else None,
            "context": context.model_dump(mode="json"),
        }

    # ------------------------------------------------------------------
    # Public sales-case facade: document intake -> confirmed profile -> V2

    @router.post("/sales-cases", status_code=status.HTTP_201_CREATED)
    def create_sales_case(
        body: CreateSalesCaseBody,
        response: Response,
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
        idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:create")
        replay_key = f"sales-case-draft:{x_employee_id}:{idempotency_key}" if idempotency_key else None
        if replay_key:
            replay = repo().get_idempotent_result(replay_key)
            if replay is not None:
                return {**replay, "idempotent_replay": True}
        safety = screen_input("\n".join(filter(None, [body.need_text, body.rm_note or ""])))
        if not safety.safe:
            raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "flags": safety.flags})
        context = assemble(x_employee_id, x_session_id)
        manual = body.model_dump(mode="json")
        manual["submission_source"] = "customer" if actor_role(x_employee_id) == "customer_user" else "rm"
        manual["need_text"] = safety.sanitized_text.split("\n", 1)[0]
        stored = intake_service().create(
            employee_id=x_employee_id,
            session_id=x_session_id,
            customer_id=context.customer.customer_id,
            manual_input=manual,
            crm_attributes=context.customer.attributes,
        )
        result = intake_payload(stored)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=stored.session.case_id,
            trace_id=f"TRACE-{uuid.uuid4().hex.upper()}", actor=x_employee_id,
            action="sales_case_draft_created", payload={"intake_id": stored.session.intake_id},
        )
        logger.emit("sales_case_draft_created", case_id=stored.session.case_id, employee_id=x_employee_id)
        metrics.increment("intake.created")
        if replay_key:
            result = repo().save_idempotent_result(replay_key, "create_sales_case", "draft", result)
        response.headers["ETag"] = str(stored.version)
        return result

    @router.get("/sales-cases/intake-suggestions")
    def get_intake_suggestions(
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:write")
        context = assemble(x_employee_id, x_session_id)
        result = _intake_assistance(context)
        logger.emit(
            "intake_suggestions_generated",
            employee_id=x_employee_id,
            customer_id=context.customer.customer_id,
            fields=list(result["database_fields"]),
            product_count=len(result["product_suggestions"]),
        )
        return result

    @router.get("/sales-cases/credit-history")
    def get_credit_history(
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
    ) -> Dict[str, Any]:
        """Fetch CIC / internal credit history for the scoped customer."""
        require_permission(x_employee_id, "case:read")
        context = assemble(x_employee_id, x_session_id)
        customer_id = context.customer.customer_id
        records = SQLiteCRMAdapter().list_credit_history(customer_id)
        worst = max((int(r["cic_group"]) for r in records), default=None)
        logger.emit(
            "credit_history_fetched",
            employee_id=x_employee_id,
            customer_id=customer_id,
            record_count=len(records),
            worst_cic_group=worst,
        )
        return {
            "customer_id": customer_id,
            "record_count": len(records),
            "worst_cic_group": worst,
            "records": records,
            "source": "credit_history (SQLite CIC mock)",
        }

    @router.get("/sales-cases")
    def list_sales_cases(x_employee_id: str = Header(...)) -> List[Dict[str, Any]]:
        require_permission(x_employee_id, "case:read")
        intakes = repo().list_intakes(x_employee_id)
        runtime_items = repo().list_cases(x_employee_id)
        if actor_role(x_employee_id) == "relationship_manager":
            scope = iam_grant(x_employee_id).get("access_scope", {}).get("managed_customer_ids", [])
            intakes = [*intakes, *repo().list_intakes_for_customers(scope)]
            runtime_items = [*runtime_items, *repo().list_cases_for_customers(scope)]
        intakes = list({item.session.case_id: item for item in intakes}.values())
        runtime = {item.state.case_id: item for item in runtime_items}
        result: List[Dict[str, Any]] = []
        for item in intakes:
            state_item = runtime.get(item.session.case_id)
            result.append(
                {
                    **intake_payload(item),
                    "runtime_status": state_item.state.status.value if state_item else None,
                    "state_version": state_item.version if state_item else None,
                    "updated_at": item.session.updated_at.isoformat(),
                }
            )
        return result

    @router.post("/sales-cases/{case_id}/documents")
    async def upload_sales_case_documents(
        case_id: str,
        response: Response,
        files: List[UploadFile] = File(...),
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:write")
        stored = intake_owned(case_id, x_employee_id)
        receipts: List[Dict[str, Any]] = []
        for file in files:
            data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            try:
                stored, document, deduplicated = intake_service().add_document(
                    stored,
                    filename=file.filename or "upload",
                    mime_type=file.content_type or "application/octet-stream",
                    data=data,
                )
            except IntakeValidationError as exc:
                raise intake_error(exc) from exc
            receipts.append({**intake_service().public_document(document), "deduplicated": deduplicated})
        response.headers["ETag"] = str(stored.version)
        logger.emit("case_documents_uploaded", case_id=stored.session.case_id, count=len(receipts))
        metrics.increment("intake.documents_uploaded", len(receipts))
        return {**intake_payload(stored), "documents": receipts}

    @router.get("/sales-cases/{case_id}/documents")
    def get_sales_case_documents(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:read")
        stored = intake_owned(case_id, x_employee_id)
        documents = repo().list_intake_documents(stored.session.intake_id)
        return {"case_id": stored.session.case_id, "documents": [intake_service().public_document(item) for item in documents]}

    @router.post("/sales-cases/{case_id}/process-documents")
    def process_sales_case_documents(
        case_id: str,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:write")
        stored = intake_owned(case_id, x_employee_id)
        try:
            stored = intake_service().process(stored)
        except IntakeValidationError as exc:
            raise intake_error(exc) from exc
        response.headers["ETag"] = str(stored.version)
        logger.emit("intake_extraction_completed", case_id=stored.session.case_id, fields=len(stored.session.extracted_fields))
        metrics.increment("intake.processed")
        return {
            **intake_payload(stored),
            "processing": {"mode": "synchronous_mvp", "jobs": repo().processing_jobs(stored.session.intake_id)},
        }

    @router.get("/sales-cases/{case_id}/processing-status")
    def sales_case_processing_status(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:read")
        stored = intake_owned(case_id, x_employee_id)
        documents = repo().list_intake_documents(stored.session.intake_id)
        return {
            "case_id": stored.session.case_id,
            "overall_status": stored.session.status.value,
            "jobs": repo().processing_jobs(stored.session.intake_id),
            "documents": [intake_service().public_document(item) for item in documents],
            "retry_after_ms": 0,
        }

    @router.get("/sales-cases/{case_id}/extracted-profile")
    def get_extracted_profile(case_id: str, response: Response, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:read")
        stored = intake_owned(case_id, x_employee_id)
        if stored.session.status in {IntakeStatus.DRAFT, IntakeStatus.FILES_UPLOADED, IntakeStatus.DOCUMENT_PROCESSING}:
            raise HTTPException(status_code=409, detail={"code": "EXTRACTION_NOT_READY"})
        response.headers["ETag"] = str(stored.version)
        return {
            **intake_payload(stored),
            "fields": [item.model_dump(mode="json") for item in stored.session.extracted_fields],
            "conflicts": [item.model_dump(mode="json") for item in stored.session.conflicts],
            "missing": stored.session.profile.missing_information if stored.session.profile else [],
        }

    @router.patch("/sales-cases/{case_id}/extracted-profile")
    def patch_extracted_profile(
        case_id: str,
        body: ProfilePatchBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:write")
        stored = intake_owned(case_id, x_employee_id)
        if stored.version != body.expected_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        try:
            stored = intake_service().patch_profile(stored, changes=body.changes, employee_id=x_employee_id)
        except IntakeValidationError as exc:
            raise intake_error(exc) from exc
        response.headers["ETag"] = str(stored.version)
        return {
            **intake_payload(stored),
            "fields": [item.model_dump(mode="json") for item in stored.session.extracted_fields],
        }

    @router.post("/sales-cases/{case_id}/confirm-profile")
    def confirm_sales_case_profile(
        case_id: str,
        body: ConfirmProfileBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:confirm")
        stored = intake_owned(case_id, x_employee_id)
        if stored.version != body.expected_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        try:
            stored = intake_service().confirm(stored, employee_id=x_employee_id, attestation=body.attestation)
        except IntakeValidationError as exc:
            raise intake_error(exc) from exc
        profile = stored.session.profile
        assert profile is not None
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id,
            trace_id=f"TRACE-{uuid.uuid4().hex.upper()}", actor=x_employee_id,
            action="customer_profile_confirmed", payload={"snapshot_hash": profile.snapshot_hash, "revision": profile.revision},
        )
        response.headers["ETag"] = str(stored.version)
        return intake_payload(stored)

    @router.post("/sales-cases/{case_id}/run-analysis")
    async def run_sales_case_analysis(
        case_id: str,
        body: RunAnalysisBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:run")
        stored_intake = intake_owned(case_id, x_employee_id)
        if stored_intake.version != body.expected_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        session_value = stored_intake.session
        if session_value.status != IntakeStatus.PROFILE_CONFIRMED or not session_value.profile or not session_value.profile.rm_confirmed:
            raise HTTPException(status_code=409, detail={"code": "PROFILE_NOT_CONFIRMED"})
        grant = iam_grant(x_employee_id)
        branch = str(grant["access_scope"].get("branch") or "DENY")
        intake_documents = repo().list_intake_documents(session_value.intake_id)
        workspace_documents = [
            WorkspaceDocument(
                document_id=item.document_id,
                document_type=item.document_type,
                version="1",
                status="verified",
                access_scope={"branch": branch},
            )
            for item in intake_documents
            if item.status == DocumentJobStatus.COMPLETED
        ]
        context = assemble(x_employee_id, session_value.session_id, workspace_documents)
        print("DEBUG CONTEXT:", context.workspace.selected_customer_id)
        attributes = dict(context.customer.attributes)
        profile = session_value.profile
        attributes.update(profile.company_identity)
        attributes.update(profile.business_profile)
        attributes.update(profile.financing_profile)
        attributes.update(profile.legal_profile)
        if profile.cash_flow_profile.get("current_status"):
            attributes["cash_flow_status"] = profile.cash_flow_profile["current_status"]
        context.customer = context.customer.model_copy(update={"attributes": attributes, "stale": False})
        now = datetime.now(timezone.utc)
        existing = repo().get_case(case_id)
        if existing is None:
            state_value = SharedCaseState(
                case_id=case_id,
                trace_id=f"TRACE-{uuid.uuid4().hex.upper()}",
                status=CaseStatus.NEW,
                context=context,
                request=Request(
                    message_id=f"MSG-{uuid.uuid4().hex[:12].upper()}",
                    text=str(session_value.manual_input.get("need_text") or "Xử lý nhu cầu doanh nghiệp"),
                    received_at=now,
                ),
                workflow=Workflow(workflow_version="2.1.0", current_node=None, tasks=[], loop_count=0),
                customer_business_snapshot=profile.model_dump(mode="json"),
                evidences=[],
                approval=Approval(status=ApprovalStatus.NOT_REQUIRED),
                audit_events=[],
                created_at=now,
                updated_at=now,
            )
            state_value = await workflow.run(state_value)
            stored_case = persist(state_value, expected_version=0)
            audit_action = "analysis_started"
        else:
            state_value = existing.state
            state_value.context = context
            state_value.customer_business_snapshot = profile.model_dump(mode="json")
            changes = [f"document:{item.document_type}" for item in workspace_documents] or ["customer.profile"]
            try:
                state_value = await workflow.resume(state_value, changes=changes)
            except ValueError as exc:

                raise HTTPException(status_code=409, detail={"code": "ANALYSIS_RESUME_REJECTED", "message": str(exc)}) from exc
            stored_case = persist(state_value, expected_version=existing.version)
            audit_action = "analysis_resumed_from_profile"
        session_value.audit_events.append(
            {"actor": "Planner", "action": audit_action, "at": now.isoformat(), "payload": {"state_version": stored_case.version}}
        )
        stored_intake = repo().save_intake(session_value, expected_version=stored_intake.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=stored_case.state.trace_id,
            actor="Planner", action=audit_action, payload={"snapshot_hash": profile.snapshot_hash, "status": stored_case.state.status.value},
        )
        response.headers["X-Trace-ID"] = stored_case.state.trace_id
        response.headers["ETag"] = str(stored_case.version)
        return {**response_payload(stored_case), "intake_version": stored_intake.version}

    @router.get("/sales-cases/{case_id}/trace")
    def get_sales_case_trace(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored_intake = intake_owned(case_id, x_employee_id)
        runtime = repo().get_case(case_id)
        runtime_events = runtime.state.audit_events if runtime else []
        return {
            "case_id": case_id,
            "trace_id": runtime.state.trace_id if runtime else None,
            "timeline": [*stored_intake.session.audit_events, *runtime_events],
            "audit_chain_valid": repo().verify_audit_chain(case_id),
            "persistent_events": repo().audit_events(case_id),
            "execution_plan": runtime.state.execution_plan if runtime else None,
        }

    @router.get("/sales-cases/{case_id}/recommendations")
    def get_sales_case_recommendations(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        return {
            "case_id": case_id,
            "status": stored.state.status.value,
            "product_result": stored.state.product_result,
            "eligibility_result": stored.state.eligibility_result,
            "evidences": [item.model_dump(mode="json") for item in stored.state.evidences],
            "execution_plan": stored.state.execution_plan,
        }

    @router.get("/sales-cases/{case_id}/missing-information")
    def get_sales_case_missing_information(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        """Return structured missing information for RM and specialist review.

        Works for both pending_information (customer must provide documents/data)
        and pending_review (specialist must review evidence failures or rule violations).
        Does NOT require operations_result to be populated -- can be called immediately
        after analysis reaches any blocking state, not only after the full pipeline runs.
        """
        stored = owned(case_id, x_employee_id)
        state = stored.state
        eligibility = state.eligibility_result or {}

        # Customer-actionable missing items: fields/documents the RM or customer must provide
        customer_action_items: List[Dict[str, Any]] = []
        # Items requiring specialist review: evidence failures or non-information-gap rule blocks
        specialist_review_items: List[Dict[str, Any]] = []
        missing_fields: List[str] = []
        missing_documents: List[str] = []
        reason_codes: List[str] = []

        for product in eligibility.get("products", []):
            for rule in product.get("rules", []):
                rule_status = rule.get("status")
                if rule_status == "pending_information":
                    field = rule.get("field", "")
                    if field.startswith("documents.") or rule.get("failure_code", "").endswith("_MISSING"):
                        doc_type = field.replace("documents.", "")
                        if doc_type and doc_type not in missing_documents:
                            missing_documents.append(doc_type)
                        customer_action_items.append({
                            "rule_id": rule.get("rule_id"),
                            "field": field,
                            "failure_code": rule.get("failure_code"),
                            "description": f"Cần bổ sung: {field}",
                            "product_id": product.get("product_id"),
                        })
                        if "MISSING" not in reason_codes:
                            reason_codes.append("BUSINESS_INFORMATION_MISSING")
                    else:
                        if field and field not in missing_fields:
                            missing_fields.append(field)
                        customer_action_items.append({
                            "rule_id": rule.get("rule_id"),
                            "field": field,
                            "failure_code": rule.get("failure_code"),
                            "description": f"Thiếu thông tin: {field}",
                            "product_id": product.get("product_id"),
                        })
                        if "BUSINESS_INFORMATION_MISSING" not in reason_codes:
                            reason_codes.append("BUSINESS_INFORMATION_MISSING")
                elif rule_status in ("failed", "pending_review"):
                    specialist_review_items.append({
                        "rule_id": rule.get("rule_id"),
                        "field": rule.get("field"),
                        "status": rule_status,
                        "failure_code": rule.get("failure_code"),
                        "human_review_allowed": rule.get("human_review_allowed", False),
                        "product_id": product.get("product_id"),
                    })
                    if rule_status == "failed":
                        if "NON_OVERRIDABLE_RULE_FAILED" not in reason_codes and not rule.get("human_review_allowed"):
                            reason_codes.append("NON_OVERRIDABLE_RULE_FAILED")
                        elif "REVIEWABLE_RULE_FAILED" not in reason_codes and rule.get("human_review_allowed"):
                            reason_codes.append("REVIEWABLE_RULE_FAILED")
                    elif rule_status == "pending_review":
                        if "REVIEWABLE_RULE_FAILED" not in reason_codes:
                            reason_codes.append("REVIEWABLE_RULE_FAILED")

        # Evidence grounding failures (from risk gate result if available)
        invalid_evidences = [item for item in state.evidences if not item.is_valid]
        for evidence in invalid_evidences:
            code = "EVIDENCE_QUOTE_MISSING" if not evidence.quote else "EVIDENCE_PROVENANCE_INVALID"
            if code not in reason_codes:
                reason_codes.append(code)
            specialist_review_items.append({
                "claim_id": evidence.claim_id,
                "module": evidence.module,
                "source_document_id": evidence.source_document_id,
                "human_review_allowed": evidence.human_review_allowed,
                "type": "evidence_validation_failure",
            })

        # Supplement with operations_result missing_information if available
        ops_missing = []
        if state.operations_result:
            ops_missing = state.operations_result.get("missing_information", [])

        return {
            "case_id": case_id,
            "case_status": state.status.value,
            "customer_action_items": customer_action_items,
            "specialist_review_items": specialist_review_items,
            "missing_fields": missing_fields,
            "missing_documents": missing_documents,
            "reason_codes": reason_codes,
            "source_refs": [
                {"rule_id": item.get("rule_id"), "source_document_id": None}
                for item in customer_action_items + specialist_review_items
            ],
            # Legacy fields for backward compatibility
            "questions": state.next_best_questions,
            "actions": state.next_best_actions,
            "blocked_steps": [
                item.get("step_id") for item in (state.execution_plan or {}).get("steps", [])
                if item.get("status") == "blocked"
            ],
            "operations_missing_information": ops_missing,
        }

    @router.post("/sales-cases/{case_id}/approval-preview")
    def sales_case_approval_preview(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        """Return the exact immutable action bundle the RM is being asked to approve."""
        require_permission(x_employee_id, "case:read")
        stored = owned(case_id, x_employee_id)
        state_value = stored.state
        if state_value.status != CaseStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=409, detail={"code": "CASE_NOT_READY_FOR_APPROVAL"})
        frozen = action_payload(state_value)
        return {
            "case_id": case_id,
            "state_version": stored.version,
            "target": "enterprise_crm_task_email",
            "payload": frozen,
            "payload_hash": payload_hash(frozen),
            "risk_summary": {
                "eligibility": state_value.eligibility_result["overall_status"],
                "evidence_count": len(state_value.evidences),
                "external_send": False,
            },
            "reversible": False,
        }

    @router.post("/sales-cases/{case_id}/approve")
    def approve_sales_case(
        case_id: str,
        body: SalesApproveBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:approve")
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        if state_value.status != CaseStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=409, detail={"code": "CASE_NOT_READY_FOR_APPROVAL"})
        frozen = action_payload(state_value)
        current_hash = payload_hash(frozen)
        if body.payload_hash and body.payload_hash != current_hash:
            raise HTTPException(status_code=409, detail={"code": "PAYLOAD_CHANGED"})
        issued = approval_service().issue(
            case_id=case_id, approver_id=x_employee_id,
            permissions=["create_crm_case"], payload=frozen,
        )
        claims = issued["claims"]
        state_value.approval = Approval(
            status=ApprovalStatus.APPROVED,
            approver_id=x_employee_id,
            payload_hash=claims["package_hash"],
            expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
        )
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="payload_approved", payload={"payload_hash": claims["package_hash"]},
        )
        response.headers["ETag"] = str(updated.version)
        return {
            "case_id": case_id,
            "state_version": updated.version,
            "approval_token": issued["token"],
            "payload_hash": claims["package_hash"],
            "expires_at": claims["exp"],
        }

    @router.post("/sales-cases/{case_id}/reject")
    def reject_sales_case(case_id: str, body: RejectBody, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:approve")
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        if state_value.status not in {CaseStatus.PENDING_APPROVAL, CaseStatus.PENDING_REVIEW, CaseStatus.PENDING_INFORMATION}:
            raise HTTPException(status_code=409, detail={"code": "INVALID_STATE"})
        state_value.status = CaseStatus.REJECTED
        state_value.approval.status = ApprovalStatus.REJECTED
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="case_rejected", payload={"reason": body.reason},
        )
        return response_payload(updated)

    @router.post("/sales-cases/{case_id}/execute-actions")
    def execute_sales_case_actions(
        case_id: str,
        body: ExecuteBody,
        response: Response,
        x_employee_id: str = Header(...),
        x_approval_token: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:execute")
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        frozen = action_payload(state_value)
        try:
            result = executor_service().execute(
                state_value, approver_id=x_employee_id, token=x_approval_token,
                idempotency_key=body.idempotency_key, payload=frozen,
            )
        except (ApprovalError, ExecutionDenied) as exc:
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_DENIED", "message": str(exc)}) from exc
        state_value.status = CaseStatus.COMPLETED
        state_value.approval.status = ApprovalStatus.CONSUMED
        state_value.audit_events.append(
            {"actor": "ActionExecutor", "action": "actions_executed", "at": datetime.now(timezone.utc).isoformat(), "payload": {"opportunity_id": result["opportunity_id"]}}
        )
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor="ActionExecutor", action="actions_executed",
            payload={"opportunity_id": result["opportunity_id"], "task_ids": result["task_ids"], "idempotent_replay": result["idempotent_replay"]},
        )
        response.headers["ETag"] = str(updated.version)
        return {"case_id": case_id, "state_version": updated.version, "status": "completed", "result": result}

    @router.get("/sales-cases/{case_id}/audit")
    def get_sales_case_audit(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:audit")
        intake_owned(case_id, x_employee_id)
        return {
            "case_id": case_id,
            "events": repo().audit_events(case_id),
            "chain_valid": repo().verify_audit_chain(case_id),
        }

    @router.get("/sales-cases/{case_id}/ai-log")
    def get_sales_case_ai_log(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        """Expose sanitized AI/rule/retrieval decisions for RM review and evaluation."""
        require_permission(x_employee_id, "case:audit")
        stored = owned(case_id, x_employee_id)
        logs = stored.state.ai_decision_log
        return {
            "case_id": case_id,
            "trace_id": stored.state.trace_id,
            "workflow_version": stored.state.workflow.workflow_version,
            "entries": logs,
            "summary": {
                "entry_count": len(logs),
                "total_latency_ms": sum(int(item.get("latency_ms", 0)) for item in logs),
                "total_tokens": sum(int(item.get("token_usage", {}).get("total", 0)) for item in logs),
                "estimated_cost": sum(float(item.get("estimated_cost", 0.0)) for item in logs),
                "raw_pii_logged": any(bool(item.get("safety", {}).get("raw_pii_logged")) for item in logs),
            },
        }

    @router.post("/cases", status_code=status.HTTP_201_CREATED)
    async def create_case(
        body: CreateCaseBody,
        response: Response,
        x_employee_id: str = Header(...),
        x_session_id: str = Header(...),
    ) -> Dict[str, Any]:
        trace_id = f"TRACE-{uuid.uuid4().hex.upper()}"
        safety = screen_input(body.message)
        if not safety.safe:
            metrics.increment("safety.prompt_injection_blocked")
            logger.emit("prompt_injection_blocked", trace_id=trace_id, employee_id=x_employee_id, flags=safety.flags)
            raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "flags": safety.flags})
        case_id = f"CASE-{uuid.uuid4().hex[:12].upper()}"
        context = assemble(x_employee_id, x_session_id, body.documents, trace_id)
        now = datetime.now(timezone.utc)
        state_value = SharedCaseState(
            case_id=case_id,
            trace_id=trace_id,
            status=CaseStatus.NEW,
            context=context,
            request=Request(message_id=f"MSG-{uuid.uuid4().hex[:12].upper()}", text=safety.sanitized_text, received_at=now),
            workflow=Workflow(workflow_version="2.0.0", current_node=None, tasks=[], loop_count=0),
            evidences=[],
            approval=Approval(status=ApprovalStatus.NOT_REQUIRED),
            audit_events=[],
            created_at=now,
            updated_at=now,
        )
        state_value = await workflow.run(state_value)
        stored = persist(state_value, expected_version=0)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=trace_id,
            actor=x_employee_id, action="case_created", payload={"status": state_value.status.value, "message_id": state_value.request.message_id},
        )
        logger.emit("case_created", case_id=case_id, trace_id=trace_id, status=state_value.status.value)
        metrics.increment("cases.created")
        metrics.increment(f"cases.status.{state_value.status.value}")
        response.headers["X-Trace-ID"] = trace_id
        response.headers["ETag"] = str(stored.version)
        return response_payload(stored)

    @router.get("/cases")
    def list_cases(x_employee_id: str = Header(...)) -> List[Dict[str, Any]]:
        return [response_payload(item) for item in repo().list_cases(x_employee_id)]

    @router.get("/cases/{case_id}")
    def get_case(case_id: str, response: Response, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        response.headers["X-Trace-ID"] = stored.state.trace_id
        response.headers["ETag"] = str(stored.version)
        return response_payload(stored)

    @router.get("/cases/{case_id}/trace")
    def get_trace(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        return {
            "trace_id": stored.state.trace_id,
            "timeline": stored.state.audit_events,
            "audit_chain_valid": repo().verify_audit_chain(case_id),
            "persistent_events": repo().audit_events(case_id),
        }

    @router.post("/cases/{case_id}/messages")
    async def add_message(
        case_id: str,
        body: MessageBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        safety = screen_input(body.message)
        if not safety.safe:
            metrics.increment("safety.prompt_injection_blocked")
            raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "flags": safety.flags})
        message = safety.sanitized_text
        if body.mode == "append":
            message = f"{stored.state.request.text}\nBổ sung từ RM: {message}"
        try:
            state_value = await workflow.rerun_with_message(
                stored.state,
                message=message,
                message_id=f"MSG-{uuid.uuid4().hex[:12].upper()}",
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail={"code": "CASE_MESSAGE_REJECTED", "message": str(exc)}) from exc
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="case_message_added",
            payload={"message_id": state_value.request.message_id, "mode": body.mode},
        )
        logger.emit("case_message_added", case_id=case_id, trace_id=state_value.trace_id, mode=body.mode)
        metrics.increment("cases.messages_added")
        response.headers["ETag"] = str(updated.version)
        return response_payload(updated)

    @router.post("/cases/{case_id}/documents")
    async def add_documents(
        case_id: str,
        body: DocumentsBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        documents, changes = merge_documents(list(state_value.context.documents), body.documents)
        if not changes:
            response.headers["ETag"] = str(stored.version)
            return {**response_payload(stored), "deduplicated": True}
        state_value.context = state_value.context.model_copy(update={"documents": documents})
        try:
            if state_value.status == CaseStatus.CLARIFICATION_REQUIRED:
                state_value = await workflow.rerun_with_message(
                    state_value,
                    message=state_value.request.text,
                    message_id=f"MSG-{uuid.uuid4().hex[:12].upper()}",
                )
            else:
                state_value = await workflow.resume(state_value, changes=changes)

        except ValueError as exc:
            raise HTTPException(status_code=409, detail={"code": "CASE_DOCUMENT_REJECTED", "message": str(exc)}) from exc
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="case_documents_registered",
            payload={"changes": changes, "resume_nodes": state_value.workflow.resume_from_nodes},
        )
        metrics.increment("cases.documents_registered")
        response.headers["ETag"] = str(updated.version)
        return {**response_payload(updated), "deduplicated": False}

    @router.patch("/cases/{case_id}/context")
    async def correct_context(
        case_id: str,
        body: ContextCorrectionBody,
        response: Response,
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        allowed_fields = CONTEXT_CORRECTION_POLICIES.keys()
        prefix = "customer.attributes."
        if not body.field.startswith(prefix) or body.field[len(prefix):] not in allowed_fields:
            raise HTTPException(status_code=422, detail={"code": "CONTEXT_FIELD_NOT_CORRECTABLE"})
        state_value = stored.state
        if state_value.status in {CaseStatus.COMPLETED, CaseStatus.REJECTED}:
            raise HTTPException(status_code=409, detail={"code": "TERMINAL_CASE_IMMUTABLE"})
        field_name = body.field[len(prefix):]
        approval_was_active = state_value.approval.status in {ApprovalStatus.PENDING, ApprovalStatus.APPROVED}
        attributes = dict(state_value.context.customer.attributes)
        old_value = attributes.get(field_name)
        attributes[field_name] = body.new_value
        customer = state_value.context.customer.model_copy(update={"attributes": attributes, "stale": False})
        facts = dict(state_value.context.conversation.confirmed_facts)
        facts[field_name] = ResolvedValue(
            value=body.new_value,
            source_type=SourceType.USER_EXPLICIT,
            source_id=f"context_correction:{uuid.uuid4().hex[:8]}",
            confidence=1.0,
            confirmed=True,
            observed_at=datetime.now(timezone.utc),
        )
        conversation = state_value.context.conversation.model_copy(update={"confirmed_facts": facts})
        state_value.context = state_value.context.model_copy(
            update={"customer": customer, "conversation": conversation}
        )
        try:
            if state_value.status == CaseStatus.CLARIFICATION_REQUIRED:
                state_value = await workflow.rerun_with_message(
                    state_value,
                    message=state_value.request.text,
                    message_id=f"MSG-{uuid.uuid4().hex[:12].upper()}",
                )
            else:
                state_value = await workflow.resume(state_value, changes=[body.field])

        except ValueError as exc:
            raise HTTPException(status_code=409, detail={"code": "CONTEXT_CORRECTION_REJECTED", "message": str(exc)}) from exc
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="context_corrected",
            payload={"field": body.field, "old_value_hash": hashlib.sha256(str(old_value).encode()).hexdigest(), "reason": body.reason},
        )
        logger.emit("context_corrected", case_id=case_id, trace_id=state_value.trace_id, field=body.field)
        metrics.increment("context.corrected")
        response.headers["ETag"] = str(updated.version)
        return {
            **response_payload(updated),
            "impacted_nodes": state_value.workflow.resume_from_nodes,
            "approval_invalidated": approval_was_active,
        }

    @router.post("/cases/{case_id}/resume")
    async def resume_case(case_id: str, body: ResumeBody, response: Response, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        state_value = stored.state
        documents, detected_changes = merge_documents(list(state_value.context.documents), body.documents)
        state_value.context = state_value.context.model_copy(update={"documents": documents})
        changes = body.changes or detected_changes
        if not changes:
            response.headers["ETag"] = str(stored.version)
            return {**response_payload(stored), "deduplicated": True}
        state_value = await workflow.resume(state_value, changes=changes)

        updated = persist(state_value, expected_version=body.expected_state_version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="case_resumed", payload={"changes": changes, "resume_nodes": state_value.workflow.resume_from_nodes},
        )
        logger.emit("case_resumed", case_id=case_id, trace_id=state_value.trace_id, resume_nodes=state_value.workflow.resume_from_nodes)
        metrics.increment("workflow.resumed")
        response.headers["ETag"] = str(updated.version)
        return response_payload(updated)

    @router.post("/cases/{case_id}/approval-preview")
    def approval_preview(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        state_value = stored.state
        if state_value.status != CaseStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=409, detail={"code": "CASE_NOT_READY_FOR_APPROVAL"})
        payload = action_payload(state_value)
        return {
            "case_id": case_id,
            "state_version": stored.version,
            "action": "create_crm_case",
            "target": "enterprise_crm",
            "payload": payload,
            "payload_hash": payload_hash(payload),
            "risk_summary": {"eligibility": state_value.eligibility_result["overall_status"], "evidence_count": len(state_value.evidences)},
            "reversible": False,
        }

    @router.post("/cases/{case_id}/approve")
    def approve_case(case_id: str, body: ApproveBody, response: Response, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        if state_value.status != CaseStatus.PENDING_APPROVAL:
            raise HTTPException(status_code=409, detail={"code": "CASE_NOT_READY_FOR_APPROVAL"})
        payload = action_payload(state_value)
        issued = approval_service().issue(
            case_id=case_id, approver_id=x_employee_id, permissions=["create_crm_case"], payload=payload
        )
        claims = issued["claims"]
        state_value.approval = Approval(
            status=ApprovalStatus.APPROVED, approver_id=x_employee_id,
            payload_hash=claims["package_hash"], expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc),
        )
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="payload_approved", payload={"payload_hash": claims["package_hash"], "token_id": claims["jti"]},
        )
        logger.emit("payload_approved", case_id=case_id, trace_id=state_value.trace_id, payload_hash=claims["package_hash"])
        metrics.increment("approval.issued")
        response.headers["ETag"] = str(updated.version)
        return {"case_id": case_id, "state_version": updated.version, "approval_token": issued["token"], "expires_at": claims["exp"]}

    @router.post("/cases/{case_id}/execute")
    def execute_case(
        case_id: str,
        body: ExecuteBody,
        response: Response,
        x_employee_id: str = Header(...),
        x_approval_token: str = Header(...),
    ) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        payload = action_payload(state_value)
        try:
            result = executor_service().execute(
                state_value, approver_id=x_employee_id, token=x_approval_token,
                idempotency_key=body.idempotency_key, payload=payload,
            )
        except (ApprovalError, ExecutionDenied) as exc:
            metrics.increment("actions.denied")
            raise HTTPException(status_code=409, detail={"code": "EXECUTION_DENIED", "message": str(exc)}) from exc
        state_value.status = CaseStatus.COMPLETED
        state_value.approval.status = ApprovalStatus.CONSUMED
        state_value.audit_events.append({"actor": "ActionExecutor", "action": "actions_executed", "at": datetime.now(timezone.utc).isoformat(), "payload": {"crm_case_id": result["crm_case_id"]}})
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor="ActionExecutor", action="actions_executed", payload={"crm_case_id": result["crm_case_id"], "idempotent_replay": result["idempotent_replay"]},
        )
        logger.emit("actions_executed", case_id=case_id, trace_id=state_value.trace_id, crm_case_id=result["crm_case_id"])
        metrics.increment("actions.executed")
        response.headers["ETag"] = str(updated.version)
        return {"case_id": case_id, "state_version": updated.version, "status": "completed", "result": result}

    @router.post("/cases/{case_id}/reject")
    def reject_case(case_id: str, body: RejectBody, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        stored = owned(case_id, x_employee_id)
        if stored.version != body.expected_state_version:
            raise HTTPException(status_code=409, detail={"code": "STATE_VERSION_CONFLICT"})
        state_value = stored.state
        state_value.status = CaseStatus.REJECTED
        state_value.approval.status = ApprovalStatus.REJECTED
        updated = persist(state_value, expected_version=stored.version)
        repo().append_audit(
            event_id=f"EVT-{uuid.uuid4().hex}", case_id=case_id, trace_id=state_value.trace_id,
            actor=x_employee_id, action="case_rejected", payload={"reason": body.reason},
        )
        return response_payload(updated)

    @router.get("/knowledge/products/search")
    def search_products(
        q: str,
        x_employee_id: str = Header(...),
        top_k: int = Query(default=5, ge=1, le=10),
    ) -> Dict[str, Any]:
        grant = iam_grant(x_employee_id)
        branch = str(grant["access_scope"].get("branch") or "DENY")
        hits = ProductKnowledgeService().search(q, branch=branch, top_k=top_k)
        metrics.increment("rag.search")
        if not hits:
            metrics.increment("rag.empty")
        return {"query": q, "hits": [item.model_dump(mode="json") for item in hits]}

    @router.get("/knowledge/legal/search")
    def search_legal(
        q: str,
        product_id: Optional[str] = Query(default=None),
        top_k: int = Query(default=5, ge=1, le=10),
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        grant = iam_grant(x_employee_id)
        branch = str(grant["access_scope"].get("branch") or "DENY")
        hits = LegalKnowledgeService().search(
            q,
            branch=branch,
            product_id=product_id,
            top_k=top_k,
        )
        metrics.increment("legal_rag.search")
        if not hits:
            metrics.increment("legal_rag.empty")
        return {
            "query": q,
            "decision_owner": "EligibilityEngine",
            "hits": [item.model_dump(mode="json") for item in hits],
        }

    @router.post("/knowledge/documents/inspect")
    async def inspect_document(
        file: UploadFile = File(...),
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        grant = iam_grant(x_employee_id)
        if "case:write" not in grant["permissions"]:
            raise HTTPException(status_code=403, detail={"code": "DOCUMENT_INSPECT_DENIED"})
        filename = file.filename or "upload"
        data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
        if len(data) > settings.MAX_UPLOAD_BYTES:
            metrics.increment("documents.rejected_size")
            raise HTTPException(status_code=413, detail={"code": "DOCUMENT_TOO_LARGE"})
        try:
            sections = parse_document_bytes(filename, data)
        except UnsupportedDocumentError as exc:
            raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_DOCUMENT_TYPE"}) from exc
        except (ValueError, OSError, UnicodeError) as exc:
            raise HTTPException(status_code=422, detail={"code": "DOCUMENT_PARSE_FAILED"}) from exc
        quality = extraction_quality(sections)
        injection_locations = [
            section.location for section in sections if not screen_input(section.text).safe
        ]
        quality["prompt_injection_flags"] = len(injection_locations)
        quality["publishable"] = bool(quality["publishable"] and not injection_locations)
        content_hash = "sha256:" + hashlib.sha256(data).hexdigest()
        metrics.increment("documents.inspected")
        if not quality["publishable"]:
            metrics.increment("documents.quarantined")
        return {
            "filename": filename,
            "content_type": file.content_type,
            "size_bytes": len(data),
            "content_hash": content_hash,
            "quality": quality,
            "status": "ready_for_governed_ingestion" if quality["publishable"] else "quarantined",
            "injection_locations": injection_locations,
            "sections": [
                {
                    "location": section.location,
                    "preview": section.text[:500],
                    "metadata": section.metadata,
                }
                for section in sections
            ],
        }

    @router.post("/knowledge/documents/ingest")
    async def ingest_document(
        file: UploadFile = File(...),
        source_id: str = Form(...),
        document_id: str = Form(...),
        document_version: str = Form(...),
        product_id: str = Form(...),
        effective_from: str = Form(...),
        effective_to: Optional[str] = Form(default=None),
        segments: str = Form(default=""),
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        grant = iam_grant(x_employee_id)
        if "knowledge:write" not in grant["permissions"]:
            metrics.increment("security.knowledge_write_denied")
            raise HTTPException(status_code=403, detail={"code": "KNOWLEDGE_INGEST_DENIED"})
        source_registry = {
            "SYNTHETIC-PRODUCT-CATALOG-V2": (PRODUCT_SOURCE_CARD, ProductKnowledgeService().index),
            "SYNTHETIC-LEGAL-KNOWLEDGE-V2": (LEGAL_SOURCE_CARD, LegalKnowledgeService().index),
        }
        if source_id not in source_registry:
            raise HTTPException(status_code=422, detail={"code": "SOURCE_CARD_NOT_REGISTERED"})
        filename = file.filename or "upload"
        data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
        if len(data) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail={"code": "DOCUMENT_TOO_LARGE"})
        try:
            effective_start = date.fromisoformat(effective_from)
            effective_end = date.fromisoformat(effective_to) if effective_to else None
            source_card_path, target_index = source_registry[source_id]
            result = GovernedUploadIngestionService(target_index).ingest(
                filename=filename,
                data=data,
                source_card_path=source_card_path,
                document_id=document_id,
                document_version=document_version,
                product_id=product_id,
                effective_from=effective_start,
                effective_to=effective_end,
                branch=str(grant["access_scope"].get("branch") or "DENY"),
                segments=[item.strip() for item in segments.split(",") if item.strip()],
            )
        except UnsupportedDocumentError as exc:
            raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_DOCUMENT_TYPE"}) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "KNOWLEDGE_INGEST_INVALID", "message": str(exc)}) from exc
        metrics.increment(f"knowledge.ingest.{result['status']}")
        logger.emit(
            "knowledge_document_ingested",
            employee_id=x_employee_id,
            source_id=source_id,
            document_id_hash=hashlib.sha256(document_id.encode()).hexdigest(),
            status=result["status"],
            indexed=result["indexed"],
        )
        return result

    @router.get("/metrics")
    def local_metrics(x_employee_id: str = Header(...)) -> Dict[str, Any]:
        del x_employee_id
        return {"mode": "local_process", "metrics": metrics.snapshot()}

    @router.get("/health")
    def v2_health() -> Dict[str, Any]:
        storage = repo().health()
        product_knowledge = ProductKnowledgeService()
        legal_knowledge = LegalKnowledgeService()
        product_knowledge.ensure_index()
        legal_knowledge.ensure_index()
        product_index = product_knowledge.index.count()
        legal_index = legal_knowledge.index.count()
        product_rag_health = product_knowledge.rag_health()
        legal_rag_health = legal_knowledge.rag_health()
        rag_overall = "healthy"
        if product_rag_health["status"] == "unavailable" or legal_rag_health["status"] == "unavailable":
            rag_overall = "degraded"
        return {
            "status": "ok" if storage.get("healthy") else "degraded",
            "data_mode": "SHB_ENTERPRISE_DATA",
            "storage": storage,
            "indexes": {"product_chunks": product_index, "legal_chunks": legal_index},
            # Additive field -- does not change any existing key above.
            "rag_provider": {
                "status": rag_overall,
                "mode": settings.RAG_PROVIDER,
                "providers": {"product": product_rag_health, "legal": legal_rag_health},
            },
        }

    @router.get("/ready")
    def v2_ready(response: Response) -> Dict[str, Any]:
        """Readiness probe: 200 when storage + at least local retrieval work,
        503 when nothing usable is available. See docs/RAG_PROVIDER_AND_FALLBACK.md."""
        storage = repo().health()
        product_knowledge = ProductKnowledgeService()
        legal_knowledge = LegalKnowledgeService()
        product_rag_health = product_knowledge.rag_health()
        legal_rag_health = legal_knowledge.rag_health()
        degraded = product_rag_health["status"] == "unavailable" or legal_rag_health["status"] == "unavailable"
        unavailable = not storage.get("healthy")
        if unavailable:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable" if unavailable else ("degraded" if degraded else "healthy"),
            "storage_healthy": bool(storage.get("healthy")),
            "rag_provider_mode": settings.RAG_PROVIDER,
            "rag_providers": {"product": product_rag_health, "legal": legal_rag_health},
        }

    @router.get("/sales-cases/{case_id}/checklist")
    def get_sales_case_checklist(case_id: str, x_employee_id: str = Header(...)) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:read")
        stored = owned(case_id, x_employee_id)
        checklist = stored.state.case_checklist
        if not checklist:
            raise HTTPException(status_code=404, detail={"code": "CHECKLIST_NOT_FOUND"})
        return {"case_id": case_id, "checklist": checklist}

    @router.post("/sales-cases/{case_id}/checklist/{item_id}/documents")
    async def upload_checklist_item_documents(
        case_id: str,
        item_id: str,
        response: Response,
        files: List[UploadFile] = File(...),
        x_employee_id: str = Header(...),
    ) -> Dict[str, Any]:
        require_permission(x_employee_id, "case:write")
        stored_case = owned(case_id, x_employee_id)
        
        checklist = stored_case.state.case_checklist
        if not checklist:
            raise HTTPException(status_code=404, detail={"code": "CHECKLIST_NOT_FOUND"})
            
        item_exists = any(item.get("item_id") == item_id for item in checklist.get("items", []))
        if not item_exists:
            raise HTTPException(status_code=404, detail={"code": "CHECKLIST_ITEM_NOT_FOUND"})
            
        try:
            stored_intake = intake_owned(case_id, x_employee_id)
        except HTTPException:
            raise HTTPException(status_code=400, detail={"code": "NO_ACTIVE_INTAKE_SESSION"})

        receipts: List[Dict[str, Any]] = []
        for file in files:
            data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
            try:
                stored_intake, document, deduplicated = intake_service().add_document(
                    stored_intake,
                    filename=file.filename or "upload",
                    mime_type=file.content_type or "application/octet-stream",
                    data=data,
                )
            except IntakeValidationError as exc:
                raise intake_error(exc) from exc
            receipts.append({**intake_service().public_document(document), "deduplicated": deduplicated, "checklist_item_id": item_id})
            
        response.headers["ETag"] = str(stored_case.version)
        return {"case_id": case_id, "checklist_item_id": item_id, "documents": receipts}

    return router


router = create_router()
