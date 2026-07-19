"""PostgreSQL storage layer for employee personalization, consent, habits, and work items."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.config import settings
from app.storage import pg
from app.schemas.v2.employee import (
    EmployeeContextSnapshot,
    AuthorizationContext,
    WorkContext,
    PersonalizationContext,
    HabitModel,
    HabitStatus,
    ConsentModel,
    RoleType,
    ProvenanceMetadata,
    ProvenanceType,
)

def get_db_connection():
    # PostgreSQL connection (target from settings.DATABASE_URL). The returned
    # connection uses a cursor that accepts the legacy "?" placeholder style and
    # yields dict-like rows, so the rest of this module is unchanged apart from
    # a few dialect fixes (ON CONFLICT instead of INSERT OR IGNORE/REPLACE).
    return pg.raw_connection()


def init_employee_db() -> None:
    """Initialize employee tables and seed mock data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Local persona mirror. Keep it separate from enterprise SSO `employees`.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_personas (
        employee_id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        organization_unit TEXT NOT NULL,
        permissions TEXT NOT NULL, -- JSON list
        customer_scope TEXT NOT NULL -- JSON list
    )
    """)

    # 2. Preferences table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_preferences (
        employee_id TEXT PRIMARY KEY,
        preferences_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 3. Habits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_habits (
        habit_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        habit_type TEXT NOT NULL,
        value_json TEXT NOT NULL,
        status TEXT NOT NULL, -- candidate, confirmed, rejected
        observed_count INTEGER DEFAULT 0,
        confidence REAL DEFAULT 1.0,
        confirmed_at TEXT,
        decayed_at TEXT
    )
    """)

    # 4. Consent table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_consent (
        employee_id TEXT PRIMARY KEY,
        personalization_enabled INTEGER NOT NULL, -- 0 or 1
        activity_learning_enabled INTEGER NOT NULL,
        allowed_event_categories TEXT NOT NULL, -- JSON list
        consent_version TEXT NOT NULL,
        confirmed_at TEXT NOT NULL
    )
    """)

    # 5. Work items table (for Next Best Work)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_work_items (
        item_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL, -- pending, ready, completed
        business_impact REAL NOT NULL,
        urgency REAL NOT NULL,
        customer_commitment REAL NOT NULL,
        risk_severity REAL NOT NULL,
        dependency_unblock REAL NOT NULL,
        ownership_match REAL NOT NULL,
        estimated_effort REAL NOT NULL,
        created_at TEXT NOT NULL,
        due_at TEXT,
        dependency_ids TEXT NOT NULL, -- JSON list of blocked item_ids
        role_required TEXT NOT NULL,
        customer_id TEXT NOT NULL
    )
    """)

    # 6. Recommendation Feedback table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_recommendation_feedback (
        feedback_id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        recommendation_id TEXT NOT NULL,
        feedback TEXT NOT NULL, -- accepted, edited, rejected
        original_value TEXT, -- JSON
        edited_value TEXT, -- JSON
        confirmed_at TEXT NOT NULL
    )
    """)

    # 7. Specialist Review table -- the action surface Product/Legal/
    # Credit Specialist needs for governed human review (every case-mutating
    # endpoint in app/api/v2/router.py is RM-owned-only). case_version pins
    # a review to the exact case state it resolved, so a stale clearance
    # from a previous PENDING_REVIEW episode can never silently satisfy a
    # new one (see cleared_roles_for_case_version below).
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS specialist_reviews (
        review_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        case_version INTEGER NOT NULL,
        reviewer_employee_id TEXT NOT NULL,
        review_type TEXT NOT NULL,
        decision TEXT NOT NULL, -- cleared, blocked, needs_more_information
        summary TEXT NOT NULL,
        findings_json TEXT NOT NULL,
        required_information_json TEXT NOT NULL,
        evidence_ids_json TEXT NOT NULL,
        case_status_changed INTEGER NOT NULL, -- 0/1
        advisory_only INTEGER NOT NULL, -- 0/1
        created_at TEXT NOT NULL
    )
    """)

    # 8. Operational Readiness table -- a MANUAL, human-maintained tracker
    # for Operations Specialist, deliberately separate from
    # OperationsService's auto-computed checklist (which recomputes from
    # document status on every analysis run and cannot be durably ticked
    # off by a person). One current snapshot per case_id (upsert). Never
    # read by CaseStatus/risk-gate logic -- advisory to the RM only.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operational_readiness (
        case_id TEXT PRIMARY KEY,
        status TEXT NOT NULL, -- ready, not_ready
        items_json TEXT NOT NULL,
        summary TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed mock data if empty
    cursor.execute("SELECT COUNT(*) AS n FROM employee_personas")
    if cursor.fetchone()["n"] == 0:
        # Seed Employees
        employees_data = [
            ("USER-MP-001", "customer_user", "Minh Phat Customer Portal",
             json.dumps(["case:create", "case:read", "case:write"]),
             json.dumps(["COMP-MP"])),
            ("RM-999", "relationship_manager", "Corporate Banking HN", 
             json.dumps(["case:read", "case:write", "approval:request", "credit:forward"]),
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"])),
            ("SPEC-LEGAL-001", "legal_specialist", "Legal & Compliance Dept", 
             json.dumps(["case:read", "case:verify_evidence"]), 
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"])),
            ("SPEC-PROD-001", "product_specialist", "Product Development Dept", 
             json.dumps(["case:read", "product:recommend"]), 
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"])),
            ("SPEC-CREDIT-001", "credit_specialist", "Credit Risk & Underwriting", 
             json.dumps(["case:read", "credit:analyze_file", "credit:review_structure", "credit:appraise"]),
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"])),
            ("SPEC-INSURANCE-001", "insurance_specialist", "Corporate Insurance Advisory",
             json.dumps(["case:read", "insurance:analyze_coverage", "insurance:review_coverage", "insurance:manage_knowledge"]),
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"])),
            ("MGR-HN-01", "manager", "Branch HN Management", 
             json.dumps(["team:view_workload", "case:read", "credit:final_approve"]),
             json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"]))
        ]
        cursor.executemany(
            "INSERT INTO employee_personas VALUES (?, ?, ?, ?, ?)", employees_data
        )

        # Seed default Preferences
        cursor.execute(
            "INSERT INTO employee_preferences VALUES (?, ?, ?)",
            ("RM-999", json.dumps({
                "default_case_view": "missing_information",
                "preferred_email_template": "formal_corporate",
                "show_evidence_expanded": True
            }), datetime.utcnow().isoformat())
        )

        # Seed default Consent
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("USER-MP-001", 0, 0, json.dumps([]), "v1", datetime.utcnow().isoformat())
        )
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("RM-999", 1, 1, json.dumps(["ui_preferences", "recommendation_feedback"]), "v1", datetime.utcnow().isoformat())
        )
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("SPEC-LEGAL-001", 1, 0, json.dumps(["ui_preferences"]), "v1", datetime.utcnow().isoformat())
        )
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("SPEC-CREDIT-001", 1, 0, json.dumps(["ui_preferences"]), "v1", datetime.utcnow().isoformat())
        )
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("SPEC-INSURANCE-001", 1, 0, json.dumps(["ui_preferences"]), "v1", datetime.utcnow().isoformat())
        )
        cursor.execute(
            "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?)",
            ("MGR-HN-01", 1, 0, json.dumps([]), "v1", datetime.utcnow().isoformat())
        )

        # Seed mock Work Items for Next Best Work demo (Minh Phát COMP-MP tasks)
        # We need a variety of tasks to show ranking in E2E
        work_items = [
            # Expired legal deadline / Regulatory (Band P0)
            ("TASK-101", "RM-999", "Bổ sung tờ trình pháp lý Minh Phát", "pending",
             0.8, 1.0, 0.9, 0.9, 0.7, 1.0, 0.3, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "relationship_manager", "COMP-MP"),

            # SLA Breach / High risk (Band P1)
            ("TASK-102", "RM-999", "Review hồ sơ tài chính mới của Công ty Minh Phát", "pending",
             0.9, 0.8, 0.8, 0.7, 0.9, 1.0, 0.4, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "relationship_manager", "COMP-MP"),

            # Customer Commitment (Band P2) — title cues Product Agent suggestions
            ("TASK-103", "RM-999", "Gửi email đề xuất chi lương + thanh toán hóa đơn điện", "pending",
             0.7, 0.5, 1.0, 0.3, 0.5, 1.0, 0.2, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "relationship_manager", "COMP-MP"),

            # Normal Opportunity Work (Band P3)
            ("TASK-104", "RM-999", "Giới thiệu gói cash management và vốn lưu động Minh Phát", "pending",
             0.5, 0.2, 0.0, 0.2, 0.3, 1.0, 0.5, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "relationship_manager", "COMP-MP"),

            # Legal Specialist Task (Assigned to Legal)
            ("TASK-201", "SPEC-LEGAL-001", "Thẩm định điều kiện UBO chưa xác minh Minh Phát", "pending",
             0.8, 0.7, 0.5, 0.8, 0.8, 1.0, 0.6, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "legal_specialist", "COMP-MP"),

            # Product Specialist Task (Assigned to Product)
            ("TASK-301", "SPEC-PROD-001", "Xác nhận product-fit gói Cash Management", "pending",
             0.9, 0.6, 0.4, 0.4, 0.6, 1.0, 0.3, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "product_specialist", "COMP-MP"),

            # Credit Specialist Task (Assigned to Credit Expert owner)
            ("TASK-401", "SPEC-CREDIT-001", "Phân tích khả năng trả nợ và cấu trúc vốn lưu động Minh Phát", "pending",
             0.95, 0.8, 0.7, 0.85, 0.8, 1.0, 0.6,
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "credit_specialist", "COMP-MP"),

            # Insurance Specialist Task (Assigned to Insurance Expert owner)
            ("TASK-501", "SPEC-INSURANCE-001", "Rà soát yêu cầu bảo hiểm cho hồ sơ Minh Phát", "pending",
             0.75, 0.5, 0.6, 0.7, 0.5, 1.0, 0.4,
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps([]), "insurance_specialist", "COMP-MP"),

            # Task blocked by dependency (Should be filtered out)
            ("TASK-105", "RM-999", "Thực thi giải ngân tài chính Minh Phát", "pending",
             1.0, 0.9, 1.0, 0.8, 1.0, 1.0, 0.8, 
             datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
             json.dumps(["TASK-102"]), "relationship_manager", "COMP-MP")
        ]
        cursor.executemany(
            "INSERT INTO employee_work_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            work_items
        )

        # Seed Synthetic Habits for demo
        cursor.execute(
            "INSERT INTO employee_habits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("HABIT-001", "RM-999", "review_sequence", 
             json.dumps(["customer_snapshot", "missing_information"]), 
             "confirmed", 15, 0.89, datetime.utcnow().isoformat(), None)
        )
        cursor.execute(
            "INSERT INTO employee_habits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("HABIT-002", "RM-999", "default_email_template", 
             json.dumps("formal_corporate"), 
             "candidate", 8, 0.78, None, None)
        )

        conn.commit()

    # Idempotent role migration for existing demo databases. Historical
    # specialist_reviews/audit records are intentionally retained, while
    # the active identity, consent and queue are moved to Credit Specialist.
    cursor.execute("DELETE FROM employee_work_items WHERE employee_id = ?", ("SPEC-OPS-001",))
    cursor.execute("DELETE FROM employee_preferences WHERE employee_id = ?", ("SPEC-OPS-001",))
    cursor.execute("DELETE FROM employee_consent WHERE employee_id = ?", ("SPEC-OPS-001",))
    cursor.execute("DELETE FROM employee_habits WHERE employee_id = ?", ("SPEC-OPS-001",))
    cursor.execute("DELETE FROM employee_personas WHERE employee_id = ?", ("SPEC-OPS-001",))
    cursor.execute(
        """
        INSERT INTO employee_personas (employee_id, role, organization_unit, permissions, customer_scope)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(employee_id) DO UPDATE SET
            role = excluded.role,
            organization_unit = excluded.organization_unit,
            permissions = excluded.permissions,
            customer_scope = excluded.customer_scope
        """,
        (
            "USER-MP-001", "customer_user", "Minh Phat Customer Portal",
            json.dumps(["case:create", "case:read", "case:write"]),
            json.dumps(["COMP-MP"]),
        ),
    )
    cursor.execute(
        "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (employee_id) DO NOTHING",
        (
            "USER-MP-001", 0, 0, json.dumps([]),
            "v1", datetime.utcnow().isoformat(),
        ),
    )
    cursor.execute(
        """
        INSERT INTO employee_personas (employee_id, role, organization_unit, permissions, customer_scope)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(employee_id) DO UPDATE SET
            role = excluded.role,
            organization_unit = excluded.organization_unit,
            permissions = excluded.permissions,
            customer_scope = excluded.customer_scope
        """,
        (
            "SPEC-CREDIT-001", "credit_specialist", "Credit Risk & Underwriting",
            json.dumps(["case:read", "credit:analyze_file", "credit:review_structure", "credit:manage_knowledge"]),
            json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"]),
        ),
    )
    cursor.execute(
        "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (employee_id) DO NOTHING",
        (
            "SPEC-CREDIT-001", 1, 0, json.dumps(["ui_preferences"]),
            "v1", datetime.utcnow().isoformat(),
        ),
    )
    cursor.execute(
        """
        INSERT INTO employee_personas (employee_id, role, organization_unit, permissions, customer_scope)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(employee_id) DO UPDATE SET
            role = excluded.role,
            organization_unit = excluded.organization_unit,
            permissions = excluded.permissions,
            customer_scope = excluded.customer_scope
        """,
        (
            "SPEC-INSURANCE-001", "insurance_specialist", "Corporate Insurance Advisory",
            json.dumps(["case:read", "insurance:analyze_coverage", "insurance:review_coverage", "insurance:manage_knowledge"]),
            json.dumps(["COMP-ABC", "COMP-MP", "COMP-XYZ"]),
        ),
    )
    cursor.execute(
        "INSERT INTO employee_consent VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (employee_id) DO NOTHING",
        (
            "SPEC-INSURANCE-001", 1, 0, json.dumps(["ui_preferences"]),
            "v1", datetime.utcnow().isoformat(),
        ),
    )
    cursor.execute(
        """
        INSERT INTO employee_work_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (item_id) DO NOTHING
        """,
        (
            "TASK-501", "SPEC-INSURANCE-001", "Rà soát yêu cầu bảo hiểm cho hồ sơ Minh Phát", "pending",
            0.75, 0.5, 0.6, 0.7, 0.5, 1.0, 0.4,
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            json.dumps([]), "insurance_specialist", "COMP-MP",
        ),
    )
    cursor.execute(
        """
        INSERT INTO employee_work_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (item_id) DO NOTHING
        """,
        (
            "TASK-401", "SPEC-CREDIT-001",
            "Phân tích khả năng trả nợ và cấu trúc vốn lưu động Minh Phát", "pending",
            0.95, 0.8, 0.7, 0.85, 0.8, 1.0, 0.6,
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            json.dumps([]), "credit_specialist", "COMP-MP",
        ),
    )
    conn.commit()

    conn.close()


def get_employee(employee_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_personas WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "employee_id": row["employee_id"],
            "role": row["role"],
            "organization_unit": row["organization_unit"],
            "permissions": json.loads(row["permissions"]),
            "customer_scope": json.loads(row["customer_scope"])
        }
    return None


def get_preferences(employee_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT preferences_json FROM employee_preferences WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["preferences_json"])
    return {}


def save_preferences(employee_id: str, prefs: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO employee_preferences (employee_id, preferences_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(employee_id) DO UPDATE SET
        preferences_json = excluded.preferences_json,
        updated_at = excluded.updated_at
    """, (employee_id, json.dumps(prefs), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_consent(employee_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_consent WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "employee_id": row["employee_id"],
            "personalization_enabled": bool(row["personalization_enabled"]),
            "activity_learning_enabled": bool(row["activity_learning_enabled"]),
            "allowed_event_categories": json.loads(row["allowed_event_categories"]),
            "consent_version": row["consent_version"],
            "confirmed_at": datetime.fromisoformat(row["confirmed_at"])
        }
    return None


def save_consent(consent: ConsentModel) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO employee_consent (employee_id, personalization_enabled, activity_learning_enabled, allowed_event_categories, consent_version, confirmed_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(employee_id) DO UPDATE SET
        personalization_enabled = excluded.personalization_enabled,
        activity_learning_enabled = excluded.activity_learning_enabled,
        allowed_event_categories = excluded.allowed_event_categories,
        consent_version = excluded.consent_version,
        confirmed_at = excluded.confirmed_at
    """, (
        consent.employee_id,
        1 if consent.personalization_enabled else 0,
        1 if consent.activity_learning_enabled else 0,
        json.dumps(consent.allowed_event_categories),
        consent.consent_version,
        consent.confirmed_at.isoformat()
    ))
    conn.commit()
    conn.close()


def get_habits(employee_id: str) -> List[HabitModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_habits WHERE employee_id = ?", (employee_id,))
    rows = cursor.fetchall()
    conn.close()

    habits = []
    for r in rows:
        habits.append(HabitModel(
            habit_id=r["habit_id"],
            habit_type=r["habit_type"],
            value=json.loads(r["value_json"]),
            status=HabitStatus(r["status"]),
            observed_count=r["observed_count"],
            confidence=r["confidence"],
            confirmed_at=datetime.fromisoformat(r["confirmed_at"]) if r["confirmed_at"] else None,
            decayed_at=datetime.fromisoformat(r["decayed_at"]) if r["decayed_at"] else None
        ))
    return habits


def confirm_habit(employee_id: str, habit_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE employee_habits
    SET status = 'confirmed', confirmed_at = ?
    WHERE employee_id = ? AND habit_id = ?
    """, (datetime.utcnow().isoformat(), employee_id, habit_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def reject_habit(employee_id: str, habit_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE employee_habits
    SET status = 'rejected', confirmed_at = NULL
    WHERE employee_id = ? AND habit_id = ?
    """, (employee_id, habit_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def delete_habit(employee_id: str, habit_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employee_habits WHERE employee_id = ? AND habit_id = ?", (employee_id, habit_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def get_work_items(employee_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_work_items WHERE employee_id = ?", (employee_id,))
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "item_id": r["item_id"],
            "employee_id": r["employee_id"],
            "title": r["title"],
            "status": r["status"],
            "business_impact": r["business_impact"],
            "urgency": r["urgency"],
            "customer_commitment": r["customer_commitment"],
            "risk_severity": r["risk_severity"],
            "dependency_unblock": r["dependency_unblock"],
            "ownership_match": r["ownership_match"],
            "estimated_effort": r["estimated_effort"],
            "created_at": datetime.fromisoformat(r["created_at"]),
            "due_at": datetime.fromisoformat(r["due_at"]) if r["due_at"] else None,
            "dependency_ids": json.loads(r["dependency_ids"]),
            "role_required": r["role_required"],
            "customer_id": r["customer_id"]
        })
    return items


def save_recommendation_feedback(
    feedback_id: str,
    employee_id: str,
    rec_id: str,
    feedback: str,
    orig_val: Optional[Dict[str, Any]] = None,
    edit_val: Optional[Dict[str, Any]] = None
) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO employee_recommendation_feedback (feedback_id, employee_id, recommendation_id, feedback, original_value, edited_value, confirmed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(feedback_id) DO UPDATE SET
        feedback = excluded.feedback,
        original_value = excluded.original_value,
        edited_value = excluded.edited_value,
        confirmed_at = excluded.confirmed_at
    """, (
        feedback_id, employee_id, rec_id, feedback,
        json.dumps(orig_val) if orig_val else None,
        json.dumps(edit_val) if edit_val else None,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def save_specialist_review(
    *,
    review_id: str,
    case_id: str,
    case_version: int,
    reviewer_employee_id: str,
    review_type: str,
    decision: str,
    summary: str,
    findings: List[Dict[str, Any]],
    required_information: List[str],
    evidence_ids: List[str],
    case_status_changed: bool,
    advisory_only: bool,
) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO specialist_reviews (
            review_id, case_id, case_version, reviewer_employee_id, review_type,
            decision, summary, findings_json, required_information_json,
            evidence_ids_json, case_status_changed, advisory_only, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id, case_id, case_version, reviewer_employee_id, review_type,
            decision, summary, json.dumps(findings), json.dumps(required_information),
            json.dumps(evidence_ids), int(case_status_changed), int(advisory_only),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def list_specialist_reviews(case_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM specialist_reviews WHERE case_id = ? ORDER BY created_at",
        (case_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "review_id": r["review_id"],
            "case_id": r["case_id"],
            "case_version": r["case_version"],
            "reviewer_employee_id": r["reviewer_employee_id"],
            "review_type": r["review_type"],
            "decision": r["decision"],
            "summary": r["summary"],
            "findings": json.loads(r["findings_json"]),
            "required_information": json.loads(r["required_information_json"]),
            "evidence_ids": json.loads(r["evidence_ids_json"]),
            "case_status_changed": bool(r["case_status_changed"]),
            "advisory_only": bool(r["advisory_only"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def cleared_roles_for_case_version(case_id: str, case_version: int) -> List[str]:
    """review_type values with decision='cleared' recorded against this
    EXACT case_version -- used to decide whether every specialist role the
    risk gate named in required_reviewer_roles has actually signed off on
    the CURRENT blocking reason, not a stale prior one."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT review_type FROM specialist_reviews "
        "WHERE case_id = ? AND case_version = ? AND decision = 'cleared'",
        (case_id, case_version),
    )
    roles = [r["review_type"] for r in cursor.fetchall()]
    conn.close()
    return roles


def create_work_item(item: Dict[str, Any]) -> None:
    """Insert (or replace) a single employee_work_items row at runtime --
    previously this table was only ever populated by init_employee_db()'s
    one-time seed; nothing could add a new item once the app was running,
    which is exactly what surfacing a specialist review result back to the
    owning RM's Next Best Work queue requires."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO employee_work_items (
            item_id, employee_id, title, status, business_impact, urgency,
            customer_commitment, risk_severity, dependency_unblock,
            ownership_match, estimated_effort, created_at, due_at,
            dependency_ids, role_required, customer_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (item_id) DO UPDATE SET
            employee_id = excluded.employee_id,
            title = excluded.title,
            status = excluded.status,
            business_impact = excluded.business_impact,
            urgency = excluded.urgency,
            customer_commitment = excluded.customer_commitment,
            risk_severity = excluded.risk_severity,
            dependency_unblock = excluded.dependency_unblock,
            ownership_match = excluded.ownership_match,
            estimated_effort = excluded.estimated_effort,
            created_at = excluded.created_at,
            due_at = excluded.due_at,
            dependency_ids = excluded.dependency_ids,
            role_required = excluded.role_required,
            customer_id = excluded.customer_id
        """,
        (
            item["item_id"], item["employee_id"], item["title"], item.get("status", "pending"),
            item.get("business_impact", 0.5), item.get("urgency", 0.5),
            item.get("customer_commitment", 0.0), item.get("risk_severity", 0.5),
            item.get("dependency_unblock", 0.0), item.get("ownership_match", 1.0),
            item.get("estimated_effort", 0.2), datetime.utcnow().isoformat(), item.get("due_at"),
            json.dumps(item.get("dependency_ids", [])), item["role_required"], item["customer_id"],
        ),
    )
    conn.commit()
    conn.close()


def save_operational_readiness(
    *, case_id: str, status: str, items: List[Dict[str, Any]], summary: str, updated_by: str,
) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO operational_readiness (case_id, status, items_json, summary, updated_by, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(case_id) DO UPDATE SET
            status = excluded.status,
            items_json = excluded.items_json,
            summary = excluded.summary,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
        """,
        (case_id, status, json.dumps(items), summary, updated_by, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_operational_readiness(case_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operational_readiness WHERE case_id = ?", (case_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "case_id": row["case_id"],
        "status": row["status"],
        "items": json.loads(row["items_json"]),
        "summary": row["summary"],
        "updated_by": row["updated_by"],
        "updated_at": row["updated_at"],
    }
