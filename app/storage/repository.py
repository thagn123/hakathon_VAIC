"""PostgreSQL-backed V2 repository with optimistic locking and hash-chained audit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional

from app.storage import pg
from app.storage.pg import Json
from app.schemas.v2.intake import CustomerBusinessSnapshot, ExtractedField, FieldConflict, IntakeDocument, IntakeSession
from app.schemas.v2.metadata import (
    AccessControl,
    MetadataEvent,
    MetadataObject,
    MetadataRelation,
    MetadataType,
    MetadataVersion,
)
from app.schemas.v2.shared_case_state import SharedCaseState
from app.storage.migrations import LATEST_SCHEMA_VERSION, apply_migrations


class StateConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredCase:
    state: SharedCaseState
    version: int


@dataclass(frozen=True)
class StoredIntake:
    session: IntakeSession
    version: int


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class V2Repository:
    def __init__(self, db_path: str | None = None) -> None:
        # db_path is accepted for backward compatibility with callers that
        # still pass settings.V2_DB_PATH, but the backend is PostgreSQL now:
        # the connection target comes from settings.DATABASE_URL (see
        # app/storage/pg.py). The argument is otherwise ignored.
        self.db_path = db_path
        self._lock = RLock()
        self._initialize()

    def _connect(self):
        return pg.connect()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL,
                    customer_id TEXT,
                    version INTEGER NOT NULL,
                    state_json JSONB NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence BIGSERIAL PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    case_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approval_tokens (
                    token_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    approver_id TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    expires_at BIGINT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata_objects (
                    object_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    access_control_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    current_version_id TEXT,
                    current_version_number INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata_versions (
                    version_id TEXT PRIMARY KEY,
                    object_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    FOREIGN KEY (object_id) REFERENCES metadata_objects(object_id)
                );
                CREATE TABLE IF NOT EXISTS metadata_relations (
                    relation_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata_events (
                    event_id TEXT PRIMARY KEY,
                    object_id TEXT NOT NULL,
                    version_id TEXT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    context_json TEXT NOT NULL
                );
                """
            )
            apply_migrations(connection)

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
            return int(row["v"])

    def health(self) -> Dict[str, Any]:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1")
                case_count = int(connection.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"])
            healthy = self.schema_version() == LATEST_SCHEMA_VERSION
            return {
                "healthy": healthy,
                "quick_check": "ok",
                "schema_version": self.schema_version(),
                "latest_schema_version": LATEST_SCHEMA_VERSION,
                "case_count": case_count,
            }
        except Exception as exc:
            return {
                "healthy": False,
                "error_code": "POSTGRES_HEALTH_CHECK_FAILED",
                "error_type": type(exc).__name__,
            }

    def save_case(self, state: SharedCaseState, *, expected_version: Optional[int] = None) -> StoredCase:
        now = datetime.now(timezone.utc)
        state = state.model_copy(update={"updated_at": now})
        employee_id = state.context.employee.employee_id
        customer_id = state.context.customer.customer_id
        with self._lock, self._connect() as connection:
            current = connection.execute("SELECT version FROM cases WHERE case_id=?", (state.case_id,)).fetchone()
            if current is None:
                if expected_version not in {None, 0}:
                    raise StateConflictError("case does not exist at expected version")
                version = 1
                connection.execute(
                    "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?)",
                    (state.case_id, employee_id, customer_id, version, Json(state.model_dump(mode="json")), now.isoformat()),
                )
            else:
                current_version = int(current["version"])
                if expected_version is not None and expected_version != current_version:
                    raise StateConflictError(f"expected version {expected_version}, current {current_version}")
                version = current_version + 1
                connection.execute(
                    "UPDATE cases SET employee_id=?, customer_id=?, version=?, state_json=?, updated_at=? WHERE case_id=?",
                    (employee_id, customer_id, version, Json(state.model_dump(mode="json")), now.isoformat(), state.case_id),
                )
        return StoredCase(state=state, version=version)

    def get_case(self, case_id: str) -> Optional[StoredCase]:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json, version FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            return None
        return StoredCase(state=SharedCaseState.model_validate(row["state_json"]), version=int(row["version"]))

    def list_cases(self, employee_id: str) -> List[StoredCase]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT state_json, version FROM cases WHERE employee_id=? ORDER BY updated_at DESC",
                (employee_id,),
            ).fetchall()
        return [StoredCase(SharedCaseState.model_validate(row["state_json"]), int(row["version"])) for row in rows]

    def list_cases_for_customers(self, customer_ids: List[str]) -> List[StoredCase]:
        """Cases belonging to any customer in customer_ids, regardless of
        owning employee_id -- for the Agent Knowledge Console's "what is my
        department's Agent working on" view (app/api/v2/knowledge_router.py),
        which scopes by identity.customer_scope (a specialist's assigned
        customers), not by case ownership like list_cases() above. Empty
        input returns no rows rather than every case in the table."""
        if not customer_ids:
            return []
        with self._connect() as connection:
            placeholders = ",".join("?" for _ in customer_ids)
            rows = connection.execute(
                f"SELECT state_json, version FROM cases WHERE customer_id IN ({placeholders}) ORDER BY updated_at DESC",
                tuple(customer_ids),
            ).fetchall()
        return [StoredCase(SharedCaseState.model_validate(row["state_json"]), int(row["version"])) for row in rows]

    def create_intake(self, session: IntakeSession) -> StoredIntake:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO intake_sessions(
                    intake_id,case_id,employee_id,customer_id,status,version,state_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    session.intake_id,
                    session.case_id,
                    session.employee_id,
                    session.customer_id,
                    session.status.value,
                    1,
                    Json(session.model_dump(mode="json")),
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )
        session.version = 1
        return StoredIntake(session=session, version=1)

    def save_intake(self, session: IntakeSession, *, expected_version: int) -> StoredIntake:
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT version FROM intake_sessions WHERE intake_id=?",
                (session.intake_id,),
            ).fetchone()
            if row is None:
                raise StateConflictError("intake session does not exist")
            current = int(row["version"])
            if current != expected_version:
                raise StateConflictError(f"expected intake version {expected_version}, current {current}")
            version = current + 1
            session.version = version
            session.updated_at = now
            connection.execute(
                """UPDATE intake_sessions SET customer_id=?,status=?,version=?,state_json=?,updated_at=?
                   WHERE intake_id=?""",
                (
                    session.customer_id,
                    session.status.value,
                    version,
                    Json(session.model_dump(mode="json")),
                    now.isoformat(),
                    session.intake_id,
                ),
            )
        return StoredIntake(session=session, version=version)

    def get_intake(self, identifier: str) -> Optional[StoredIntake]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json,version FROM intake_sessions WHERE intake_id=? OR case_id=?",
                (identifier, identifier),
            ).fetchone()
        if row is None:
            return None
        session = IntakeSession.model_validate(row["state_json"])
        session.version = int(row["version"])
        return StoredIntake(session=session, version=int(row["version"]))

    def list_intakes(self, employee_id: str) -> List[StoredIntake]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT state_json,version FROM intake_sessions WHERE employee_id=? ORDER BY updated_at DESC",
                (employee_id,),
            ).fetchall()
        result: List[StoredIntake] = []
        for row in rows:
            session = IntakeSession.model_validate(row["state_json"])
            session.version = int(row["version"])
            result.append(StoredIntake(session=session, version=int(row["version"])))
        return result

    def list_intakes_for_customers(self, customer_ids: List[str]) -> List[StoredIntake]:
        """Return intake drafts in the caller's customer scope.

        Used by an assigned RM to receive a customer-submitted intake while
        preserving the original submitter as the intake owner/audit actor.
        Empty scope is fail-closed.
        """
        if not customer_ids:
            return []
        with self._connect() as connection:
            placeholders = ",".join("?" for _ in customer_ids)
            rows = connection.execute(
                f"SELECT state_json,version FROM intake_sessions "
                f"WHERE customer_id IN ({placeholders}) ORDER BY updated_at DESC",
                tuple(customer_ids),
            ).fetchall()
        result: List[StoredIntake] = []
        for row in rows:
            session = IntakeSession.model_validate(row["state_json"])
            session.version = int(row["version"])
            result.append(StoredIntake(session=session, version=int(row["version"])))
        return result

    def save_intake_document(
        self,
        intake_id: str,
        document: IntakeDocument,
        sections: List[Dict[str, Any]],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO case_documents(
                    document_id,intake_id,sha256,status,document_json,sections_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    document.document_id,
                    intake_id,
                    document.sha256,
                    document.status.value,
                    document.model_dump_json(),
                    _canonical(sections),
                    now,
                    now,
                ),
            )

    def update_intake_document(self, intake_id: str, document: IntakeDocument) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE case_documents SET status=?,document_json=?,updated_at=?
                   WHERE intake_id=? AND document_id=?""",
                (
                    document.status.value,
                    document.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                    intake_id,
                    document.document_id,
                ),
            )

    def list_intake_documents(
        self,
        intake_id: str,
        *,
        include_sections: bool = False,
    ) -> List[Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT document_json,sections_json FROM case_documents WHERE intake_id=? ORDER BY created_at",
                (intake_id,),
            ).fetchall()
        if include_sections:
            return [
                (IntakeDocument.model_validate_json(row["document_json"]), json.loads(row["sections_json"]))
                for row in rows
            ]
        return [IntakeDocument.model_validate_json(row["document_json"]) for row in rows]

    def find_intake_document_by_hash(self, intake_id: str, digest: str) -> Optional[IntakeDocument]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document_json FROM case_documents WHERE intake_id=? AND sha256=?",
                (intake_id, digest),
            ).fetchone()
        return IntakeDocument.model_validate_json(row["document_json"]) if row else None

    def save_processing_job(
        self,
        intake_id: str,
        document_id: str,
        *,
        stage: str,
        status: str,
        error_code: Optional[str] = None,
    ) -> None:
        job_id = f"{document_id}:{stage}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO document_processing_jobs(
                    job_id,intake_id,document_id,stage,status,attempt,error_code,updated_at
                ) VALUES (?,?,?,?,?,1,?,?)
                ON CONFLICT(document_id,stage) DO UPDATE SET
                    status=excluded.status,
                    attempt=document_processing_jobs.attempt+1,
                    error_code=excluded.error_code,
                    updated_at=excluded.updated_at""",
                (job_id, intake_id, document_id, stage, status, error_code, now),
            )

    def processing_jobs(self, intake_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM document_processing_jobs WHERE intake_id=? ORDER BY updated_at,document_id",
                (intake_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_document_extractions(self, document_id: str, sections: List[Dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM document_extractions WHERE document_id=?", (document_id,))
            for index, section in enumerate(sections, start=1):
                connection.execute(
                    "INSERT INTO document_extractions VALUES (?,?,?,?,?,?)",
                    (
                        f"{document_id}:{index}",
                        document_id,
                        str(section.get("location") or f"section:{index}"),
                        str(section.get("text") or ""),
                        _canonical(section.get("metadata") or {}),
                        now,
                    ),
                )

    def replace_extracted_fields(self, intake_id: str, fields: List[ExtractedField]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM extracted_fields WHERE intake_id=?", (intake_id,))
            for field in fields:
                connection.execute(
                    "INSERT INTO extracted_fields VALUES (?,?,?,?,?,?,?,?)",
                    (
                        field.field_id,
                        intake_id,
                        field.field_name,
                        field.source_document_id,
                        field.confidence,
                        field.validation_status.value,
                        field.model_dump_json(),
                        now,
                    ),
                )

    def replace_field_conflicts(self, intake_id: str, conflicts: List[FieldConflict]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM field_conflicts WHERE intake_id=?", (intake_id,))
            for conflict in conflicts:
                connection.execute(
                    "INSERT INTO field_conflicts VALUES (?,?,?,?,?,?)",
                    (
                        conflict.conflict_id,
                        intake_id,
                        conflict.field_name,
                        int(conflict.requires_confirmation),
                        conflict.model_dump_json(),
                        now,
                    ),
                )

    def save_profile_draft(self, intake_id: str, profile: CustomerBusinessSnapshot) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO customer_profile_drafts(
                    snapshot_id,intake_id,revision,snapshot_hash,rm_confirmed,profile_json,created_at
                ) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(intake_id,revision) DO UPDATE SET
                    snapshot_hash=excluded.snapshot_hash,
                    rm_confirmed=excluded.rm_confirmed,
                    profile_json=excluded.profile_json""",
                (
                    profile.snapshot_id,
                    intake_id,
                    profile.revision,
                    profile.snapshot_hash,
                    int(profile.rm_confirmed),
                    profile.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def append_audit(self, *, event_id: str, case_id: str, trace_id: str, actor: str, action: str, payload: Dict[str, Any]) -> str:
        at = datetime.now(timezone.utc).isoformat()
        sanitized = self._sanitize(payload)
        payload_json = _canonical(sanitized)
        with self._lock, self._connect() as connection:
            previous = connection.execute(
                "SELECT event_hash FROM audit_events WHERE case_id=? ORDER BY sequence DESC LIMIT 1",
                (case_id,),
            ).fetchone()
            prev_hash = previous["event_hash"] if previous else "GENESIS"
            material = _canonical({
                "event_id": event_id,
                "case_id": case_id,
                "trace_id": trace_id,
                "at": at,
                "actor": actor,
                "action": action,
                "payload": sanitized,
                "prev_hash": prev_hash,
            })
            event_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
            connection.execute(
                "INSERT INTO audit_events(event_id,case_id,trace_id,at,actor,action,payload_json,prev_hash,event_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                (event_id, case_id, trace_id, at, actor, action, payload_json, prev_hash, event_hash),
            )
        return event_hash

    def audit_events(self, case_id: str) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM audit_events WHERE case_id=? ORDER BY sequence", (case_id,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def verify_audit_chain(self, case_id: str) -> bool:
        previous = "GENESIS"
        for row in self.audit_events(case_id):
            if row["prev_hash"] != previous:
                return False
            material = _canonical({
                "event_id": row["event_id"], "case_id": row["case_id"], "trace_id": row["trace_id"],
                "at": row["at"], "actor": row["actor"], "action": row["action"],
                "payload": row["payload"], "prev_hash": row["prev_hash"],
            })
            if hashlib.sha256(material.encode("utf-8")).hexdigest() != row["event_hash"]:
                return False
            previous = row["event_hash"]
        return True

    def register_approval(self, token_id: str, case_id: str, approver_id: str, payload_hash: str, expires_at: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approval_tokens VALUES (?, ?, ?, ?, ?, 'issued')",
                (token_id, case_id, approver_id, payload_hash, expires_at),
            )

    def consume_approval(self, token_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE approval_tokens SET status='consumed' WHERE token_id=? AND status='issued'",
                (token_id,),
            )
            return cursor.rowcount == 1

    def approval(self, token_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM approval_tokens WHERE token_id=?", (token_id,)).fetchone()
        return dict(row) if row else None

    def get_idempotent_result(self, key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT result_json FROM idempotency_records WHERE idempotency_key=?", (key,)).fetchone()
        return json.loads(row["result_json"]) if row else None

    def save_idempotent_result(self, key: str, action: str, payload_hash: str, result: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO idempotency_records VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (idempotency_key) DO NOTHING",
                (key, action, payload_hash, _canonical(result), datetime.now(timezone.utc).isoformat()),
            )
            row = connection.execute("SELECT result_json FROM idempotency_records WHERE idempotency_key=?", (key,)).fetchone()
        return json.loads(row["result_json"])

    # --- Metadata Plane Operations ---

    def save_metadata_version(self, version: MetadataVersion, event: Optional[MetadataEvent] = None) -> MetadataObject:
        """Saves a new metadata version and ensures the parent object exists/updates."""
        with self._lock, self._connect() as conn:
            # Upsert MetadataObject
            cursor = conn.execute(
                "SELECT type, access_control_json, created_at, is_active FROM metadata_objects WHERE object_id = ?",
                (version.object_id,)
            )
            row = cursor.fetchone()
            if not row:
                obj = MetadataObject(
                    object_id=version.object_id,
                    type=MetadataType.DOCUMENT,  # Temporary default; ideally provided
                    current_version_id=version.version_id,
                    current_version_number=version.version_number
                )
                conn.execute(
                    """
                    INSERT INTO metadata_objects (object_id, type, access_control_json, created_at, is_active, current_version_id, current_version_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (obj.object_id, obj.type.value, obj.access_control.model_dump_json(), obj.created_at.isoformat(), 1 if obj.is_active else 0, obj.current_version_id, obj.current_version_number)
                )
            else:
                conn.execute(
                    """
                    UPDATE metadata_objects
                    SET current_version_id = ?, current_version_number = ?
                    WHERE object_id = ? AND current_version_number < ?
                    """,
                    (version.version_id, version.version_number, version.object_id, version.version_number)
                )
                obj = MetadataObject(
                    object_id=version.object_id,
                    type=MetadataType(row["type"]),
                    access_control=AccessControl.model_validate_json(row["access_control_json"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    is_active=bool(row["is_active"]),
                    current_version_id=version.version_id,
                    current_version_number=version.version_number
                )
            
            # Insert Version
            conn.execute(
                """
                INSERT INTO metadata_versions (version_id, object_id, version_number, payload_json, content_hash, previous_hash, created_at, created_by, source_system)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version.version_id, version.object_id, version.version_number, json.dumps(version.payload), version.content_hash, version.previous_hash, version.created_at.isoformat(), version.created_by, version.source_system)
            )

            # Insert Event if provided
            if event:
                conn.execute(
                    """
                    INSERT INTO metadata_events (event_id, object_id, version_id, event_type, actor, timestamp, context_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event.event_id, event.object_id, event.version_id, event.event_type.value, event.actor, event.timestamp.isoformat(), json.dumps(event.context))
                )
            
            conn.commit()
            return obj

    def get_metadata_object(self, object_id: str) -> Optional[MetadataObject]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM metadata_objects WHERE object_id = ?", (object_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return MetadataObject(
                object_id=row["object_id"],
                type=MetadataType(row["type"]),
                access_control=AccessControl.model_validate_json(row["access_control_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                is_active=bool(row["is_active"]),
                current_version_id=row["current_version_id"],
                current_version_number=row["current_version_number"]
            )

    def get_metadata_version(self, version_id: str) -> Optional[MetadataVersion]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM metadata_versions WHERE version_id = ?", (version_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return MetadataVersion(
                version_id=row["version_id"],
                object_id=row["object_id"],
                version_number=row["version_number"],
                payload=json.loads(row["payload_json"]),
                content_hash=row["content_hash"],
                previous_hash=row["previous_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
                created_by=row["created_by"],
                source_system=row["source_system"]
            )

    @staticmethod
    def _sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
        sensitive = {"approval_token", "token", "secret", "password", "raw_email_body", "identity_number"}
        return {key: "[REDACTED]" if key.lower() in sensitive else value for key, value in payload.items()}
