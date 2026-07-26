"""Storage for the P0 cross-role workflow surfaces: customer document
requests, append-only credit-appraisal review rounds, case timeline events,
and per-recipient notifications.

These tables are additive to the two existing pipelines (SharedCaseState
`cases` in app/storage/repository.py, and the flat-column
`corporate_credit_requests` in app/storage/credit_request_repository.py) --
this module never mutates either of those tables, it only records the
cross-cutting facts (what happened, when, who should hear about it) that
neither of those tables was built to hold.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.storage import pg
from app.storage.migrations import apply_migrations

_OPEN_DOCUMENT_REQUEST_STATUSES = ("REQUESTED", "SUBMITTED", "PROCESSING")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path
        # Defensive: guarantees the new tables exist even if this is the
        # first module to touch settings.V2_DB_PATH (mirrors
        # V2Repository._initialize()'s same rationale). apply_migrations()
        # is a no-op for already-applied versions (tracked in
        # schema_migrations), so calling it per-instance is cheap and safe.
        with pg.connect(self.db_path) as connection:
            apply_migrations(connection)

    def _connect(self):
        return pg.connect(self.db_path)

    # --- Customer Document Requests ----------------------------------------

    def create_document_request(
        self,
        *,
        case_id: str,
        customer_id: str,
        created_by_role: str,
        created_by_id: str,
        document_type: str,
        title: str,
        customer_safe_reason: str,
        internal_reason: Optional[str] = None,
        credit_request_id: Optional[str] = None,
        current_document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_id = f"DOCREQ-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO customer_document_requests (
                    request_id, case_id, credit_request_id, customer_id,
                    created_by_role, created_by_id, document_type, title,
                    customer_safe_reason, internal_reason, status,
                    current_document_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REQUESTED', ?, ?)
                RETURNING *
                """,
                (
                    request_id, case_id, credit_request_id, customer_id,
                    created_by_role, created_by_id, document_type, title,
                    customer_safe_reason, internal_reason, current_document_id, now,
                ),
            ).fetchone()
            return dict(row)

    def get_document_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM customer_document_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_document_requests_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM customer_document_requests WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_document_requests_for_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM customer_document_requests WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_open_document_request_for_credit_request(self, credit_request_id: str) -> Optional[Dict[str, Any]]:
        placeholders = ",".join("?" for _ in _OPEN_DOCUMENT_REQUEST_STATUSES)
        with self._connect() as connection:
            row = connection.execute(
                f"""SELECT * FROM customer_document_requests
                   WHERE credit_request_id = ? AND status IN ({placeholders})
                   ORDER BY created_at DESC LIMIT 1""",
                (credit_request_id, *_OPEN_DOCUMENT_REQUEST_STATUSES),
            ).fetchone()
        return dict(row) if row else None

    def mark_document_submitted(self, request_id: str, *, replacement_document_id: str) -> Dict[str, Any]:
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE customer_document_requests
                SET status = 'SUBMITTED', replacement_document_id = ?, submitted_at = ?
                WHERE request_id = ? AND status IN ('REQUESTED', 'PROCESSING')
                RETURNING *
                """,
                (replacement_document_id, now, request_id),
            ).fetchone()
            if not row:
                raise ValueError("Document request is missing or not awaiting a submission.")
            return dict(row)

    def mark_document_resolved(self, request_id: str, *, status: str) -> Dict[str, Any]:
        if status not in {"VERIFIED", "REJECTED"}:
            raise ValueError(f"unsupported resolution status: {status}")
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE customer_document_requests
                SET status = ?, resolved_at = ?
                WHERE request_id = ? AND status IN ('SUBMITTED', 'PROCESSING', 'REQUESTED')
                RETURNING *
                """,
                (status, now, request_id),
            ).fetchone()
            if not row:
                raise ValueError("Document request is missing or already resolved.")
            return dict(row)

    def cancel_document_request(self, request_id: str) -> Dict[str, Any]:
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE customer_document_requests
                SET status = 'CANCELLED', resolved_at = ?
                WHERE request_id = ? AND status IN ('REQUESTED', 'SUBMITTED', 'PROCESSING')
                RETURNING *
                """,
                (now, request_id),
            ).fetchone()
            if not row:
                raise ValueError("Document request is missing or already resolved.")
            return dict(row)

    # --- Credit Request Review Rounds (append-only appraisal history) ------

    def create_review_round(
        self,
        *,
        request_id: str,
        case_id: Optional[str],
        specialist_id: str,
        recommendation: str,
        specialist_reason: Optional[str],
        appraisal_summary: Optional[str],
        appraisal_score: Optional[float],
        agent_recommendation: Optional[str],
        document_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        review_id = f"CRR-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT COALESCE(MAX(review_round), 0) AS n FROM credit_request_review_rounds WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            review_round = int(existing["n"]) + 1
            row = connection.execute(
                """
                INSERT INTO credit_request_review_rounds (
                    review_id, request_id, case_id, review_round, specialist_id,
                    recommendation, specialist_reason, appraisal_summary,
                    appraisal_score, agent_recommendation, document_request_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    review_id, request_id, case_id, review_round, specialist_id,
                    recommendation, specialist_reason, appraisal_summary,
                    appraisal_score, agent_recommendation, document_request_id, now,
                ),
            ).fetchone()
            return dict(row)

    def list_review_rounds(self, request_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM credit_request_review_rounds WHERE request_id = ? ORDER BY review_round",
                (request_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    # --- Timeline Events (append-only, real -- not derived from state) ----

    def append_timeline_event(
        self,
        *,
        case_id: str,
        event_type: str,
        actor_role: str,
        actor_id: str,
        title: str,
        description: str = "",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event_id = f"TL-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO timeline_events (
                    event_id, case_id, event_type, actor_role, actor_id,
                    title, description, entity_type, entity_id, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    event_id, case_id, event_type, actor_role, actor_id,
                    title, description, entity_type, entity_id,
                    json.dumps(metadata or {}, ensure_ascii=False), now,
                ),
            ).fetchone()
            return dict(row)

    def list_timeline_events(self, case_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM timeline_events WHERE case_id = ? ORDER BY created_at, event_id",
                (case_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            result.append(item)
        return result

    # --- Notifications -------------------------------------------------------

    def create_notification(
        self,
        *,
        recipient_id: str,
        recipient_role: str,
        type_: str,
        title: str,
        message: str,
        case_id: Optional[str] = None,
        route: Optional[str] = None,
    ) -> Dict[str, Any]:
        notification_id = f"NOTIF-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO notifications (
                    notification_id, recipient_id, recipient_role, case_id,
                    type, title, message, route, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (notification_id, recipient_id, recipient_role, case_id, type_, title, message, route, now),
            ).fetchone()
            return dict(row)

    def list_notifications(self, recipient_id: str, *, unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            if unread_only:
                rows = connection.execute(
                    "SELECT * FROM notifications WHERE recipient_id = ? AND read_at IS NULL "
                    "ORDER BY created_at DESC LIMIT ?",
                    (recipient_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM notifications WHERE recipient_id = ? ORDER BY created_at DESC LIMIT ?",
                    (recipient_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def mark_notification_read(self, notification_id: str, *, recipient_id: str) -> bool:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE notifications SET read_at = ? WHERE notification_id = ? AND recipient_id = ? AND read_at IS NULL",
                (now, notification_id, recipient_id),
            )
            return cursor.rowcount == 1
