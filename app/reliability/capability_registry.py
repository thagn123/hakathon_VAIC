"""Policy registry mapping employee roles to allowed capabilities (Policy Mapper).

Note: The source of truth for identity, roles, and permissions is SSOAdapter and IAMPort.
This registry only maps roles to policies to evaluate authorization requests at the gateway.
"""

from __future__ import annotations

from typing import Dict, List, Set
from app.schemas.v2.employee import RoleType

ROLE_CAPABILITIES: Dict[RoleType, Set[str]] = {
    RoleType.CUSTOMER_USER: {
        "case:read",
        "case:write",
        "case:create",
        "document:upload",
        "document:process",
    },
    RoleType.RM: {
        "case:read",
        "case:write",
        "case:create",
        "profile:edit",
        "specialist_review:request",
        "action:draft",
        "action:approve_own",
        "document:upload",
        "document:process",
        "credit:forward",
        "credit:create_proposal",
    },
    RoleType.PRODUCT_SPECIALIST: {
        "case:read",
        "product:recommend",
        "product:verify_fit",
        "product:add_justification",
        "proposal:review",
        "product:manage_knowledge"
    },
    RoleType.LEGAL_SPECIALIST: {
        "case:read",
        "case:verify_evidence",
        "legal:verify_evidence",
        "legal:check_issue",
        "legal:block_non_eligible",
        "proposal:review",
        "legal:manage_knowledge"
    },
    RoleType.CREDIT_SPECIALIST: {
        "case:read",
        "credit:analyze_file",
        "credit:review_structure",
        "credit:appraise",
        "credit:manage_knowledge"
    },
    RoleType.INSURANCE_SPECIALIST: {
        "case:read",
        "insurance:analyze_coverage",
        "insurance:review_coverage",
        "insurance:manage_knowledge"
    },
    RoleType.MANAGER: {
        "case:read",
        "team:view_workload",
        "team:view_blocked_cases",
        "team:view_sla_risks",
        "team:view_aggregate_utilization",
        "credit:final_approve",
    },
    RoleType.AUDITOR: {
        "case:read",
        "audit:view_history",
        "audit:export_report"
    },
    RoleType.ADMIN: {
        "system:manage_personalization",
        "system:configure_retention",
        "system:update_prompt_version"
    }
}


def has_capability(role: RoleType, capability: str) -> bool:
    """Evaluate if a role is permitted to perform a capability according to the policy mapper."""
    allowed = ROLE_CAPABILITIES.get(role, set())
    return capability in allowed
