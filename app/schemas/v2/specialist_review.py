"""Specialist Review contracts: the action surface Product/Legal/Credit
Specialist were missing (see docs/EMPLOYEE_ROLE_DESIGN_EVALUATION_REPORT.md
gap #1/#2/#3). A review resolves -- or formally cannot resolve -- the exact
reason app.workflow.risk_gate.RiskGuardrailGate put a case into
CaseStatus.PENDING_REVIEW; it never grants or expands permissions itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.v2.employee import RoleType

SpecialistDecision = Literal["cleared", "blocked", "needs_more_information"]

_REVIEWER_ROLES = {
    RoleType.LEGAL_SPECIALIST, RoleType.PRODUCT_SPECIALIST, RoleType.CREDIT_SPECIALIST,
    RoleType.INSURANCE_SPECIALIST,
}


class ForwardToSpecialistRequest(BaseModel):
    """RM action: create a real WorkItem assigning a case to a specialist
    role for review. Distinct from SpecialistReviewRequest above -- this
    never changes case status or clears/blocks anything; it only assigns
    and notifies. Only the specialist's own SpecialistReviewRequest (their
    own endpoint, their own role) can change the case's review outcome."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    specialist_role: RoleType
    reason: str = Field(min_length=3, max_length=2000)
    evidence_refs: List[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"

    @field_validator("specialist_role")
    @classmethod
    def _must_be_a_specialist_role(cls, value: RoleType) -> RoleType:
        if value not in _REVIEWER_ROLES:
            raise ValueError(f"specialist_role must be one of {sorted(r.value for r in _REVIEWER_ROLES)}")
        return value


class SpecialistReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: Literal["low", "medium", "high"]
    message: str = Field(min_length=1)


class SpecialistReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_type: RoleType
    decision: SpecialistDecision
    summary: str = Field(min_length=3)
    findings: List[SpecialistReviewFinding] = Field(default_factory=list)
    required_information: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    # Optional in this MVP round, intended to become mandatory once a pilot
    # needs strict lost-update protection (see implementation report). When
    # provided, the endpoint 409s with CASE_VERSION_CONFLICT if it no longer
    # matches the case's current state_version.
    expected_case_version: Optional[int] = Field(default=None, ge=1)

    @field_validator("review_type")
    @classmethod
    def _must_be_a_specialist_role(cls, value: RoleType) -> RoleType:
        if value not in _REVIEWER_ROLES:
            raise ValueError(f"review_type must be one of {sorted(r.value for r in _REVIEWER_ROLES)}")
        return value


class SpecialistReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    case_id: str
    case_version: int
    reviewer_employee_id: str
    review_type: RoleType
    decision: SpecialistDecision
    summary: str
    case_status: str
    case_status_changed: bool
    advisory_only: bool
    still_waiting_for: List[str] = Field(default_factory=list)
    created_at: datetime


class OperationalReadinessItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    status: Literal["pending", "completed", "blocked"]
    note: Optional[str] = None


class OperationalReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[OperationalReadinessItem] = Field(min_length=1)
    summary: str = Field(min_length=3)


class OperationalReadinessSnapshot(BaseModel):
    """A manual, human-maintained readiness tracker for Operations --
    deliberately separate from OperationsService's auto-computed
    document-status checklist (see app/workflow/engine.py's
    _analysis()/OperationsService.prepare()), which recomputes itself from
    scratch on every analysis run and is therefore not something a human
    can durably tick off. Never touches CaseStatus or legal/product
    eligibility -- see docs/SPECIALIST_REVIEW_IMPLEMENTATION_REPORT.md."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: Literal["ready", "not_ready"]
    items: List[OperationalReadinessItem]
    summary: str
    updated_by: str
    updated_at: datetime


class SpecialistReviewRecord(BaseModel):
    """Stored/listed shape for GET .../specialist-reviews (history view)."""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    case_id: str
    case_version: int
    reviewer_employee_id: str
    review_type: RoleType
    decision: SpecialistDecision
    summary: str
    findings: List[SpecialistReviewFinding] = Field(default_factory=list)
    required_information: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    case_status_changed: bool
    advisory_only: bool
    created_at: datetime
