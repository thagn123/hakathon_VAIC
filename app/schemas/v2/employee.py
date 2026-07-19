"""Pydantic schemas for the Role-Aware Employee Copilot & Work Optimization Layer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoleType(str, Enum):
    CUSTOMER_USER = "customer_user"
    RM = "relationship_manager"
    PRODUCT_SPECIALIST = "product_specialist"
    LEGAL_SPECIALIST = "legal_specialist"
    CREDIT_SPECIALIST = "credit_specialist"
    INSURANCE_SPECIALIST = "insurance_specialist"
    MANAGER = "manager"
    AUDITOR = "auditor"
    ADMIN = "admin"


class ProvenanceType(str, Enum):
    VERIFIED = "verified_context"
    DERIVED = "derived_context"
    PREFERENCE = "preference"
    CONFIRMED = "confirmed_habit"
    CANDIDATE = "candidate_habit"


class ProvenanceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_version: str
    refreshed_at: datetime
    expires_at: Optional[datetime] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    type: ProvenanceType


class AuthorizationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_verified: bool
    roles: List[RoleType]
    permissions: List[str]
    customer_scope: List[str]
    verified_at: datetime
    expires_at: Optional[datetime] = None


class WorkContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_case_id: Optional[str] = None
    assigned_customer_ids: List[str] = Field(default_factory=list)
    pending_task_ids: List[str] = Field(default_factory=list)
    blocked_case_ids: List[str] = Field(default_factory=list)
    waiting_for_roles: List[str] = Field(default_factory=list)


class HabitStatus(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class HabitModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    habit_id: str
    habit_type: str
    value: Any
    status: HabitStatus
    observed_count: int = 0
    confidence: float = 1.0
    confirmed_at: Optional[datetime] = None
    decayed_at: Optional[datetime] = None


class PersonalizationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    preferences: Dict[str, Any] = Field(default_factory=dict)
    confirmed_habits: List[HabitModel] = Field(default_factory=list)
    context_version: int = 1
    # True only when the personalization store itself failed and defaults
    # were substituted (fail-soft) -- distinct from `enabled=False`, which
    # means the employee deliberately opted out. A caller/UI needs to tell
    # "you turned this off" apart from "this is temporarily degraded".
    personalization_degraded: bool = False


class VerifiedIdentity(BaseModel):
    """The single, verified identity object every /api/v2/me/* and
    /api/v2/recommendations/* route depends on. Never constructed from
    request-body or query-parameter data -- only from
    require_verified_identity() in app/api/v2/employee_router.py, which is
    the one place identity is resolved via SSOPort/IAMPort."""

    model_config = ConfigDict(extra="forbid")

    employee_id: str
    session_id: str
    roles: List[RoleType]
    permissions: List[str] = Field(default_factory=list)
    customer_scope: List[str] = Field(default_factory=list)
    organization_unit: str = ""
    auth_source: Literal["sso", "demo"]
    identity_verified: bool


class EmployeeContextSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    authorization_context: AuthorizationContext
    work_context: WorkContext
    personalization_context: PersonalizationContext
    provenance_map: Dict[str, ProvenanceMetadata] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class NextBestWorkItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_item_id: str
    title: str
    customer_id: str = ""
    priority_score: float = Field(ge=0.0, le=100.0)
    priority: str  # "high", "medium", "low"
    reasons: List[str]
    excluded_actions: List[str] = Field(default_factory=list)
    recommended_action: str
    # Agent gợi ý dịch vụ ngân hàng để RM điền thêm vào hồ sơ (không phải mã nội bộ).
    agent_suggestions: List[str] = Field(default_factory=list)


class ConsentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    personalization_enabled: bool
    activity_learning_enabled: bool
    allowed_event_categories: List[str] = Field(default_factory=list)
    consent_version: str = "v1"
    confirmed_at: datetime
