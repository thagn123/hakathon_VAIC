"""PostgreSQL persistence for customer credit requests."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Sequence

from app.schemas.v2.credit_request import CorporateCreditRequestCreate
from app.storage import pg
from app.storage.pg import Json


class CreditRequestConflict(RuntimeError):
    pass


class CreditRequestRepository:
    def create(
        self,
        request: CorporateCreditRequestCreate,
        *,
        submitted_by: str,
        idempotency_key: str,
        service_advisory: Dict[str, Any],
    ) -> Dict[str, Any]:
        with pg.connect() as connection:
            existing = connection.execute(
                """SELECT * FROM corporate_credit_requests
                   WHERE submitted_by = ? AND submission_idempotency_key = ?""",
                (submitted_by, idempotency_key),
            ).fetchone()
            if existing:
                return dict(existing)

            request_id = f"CR-{uuid.uuid4().hex[:12].upper()}"
            case_id = request.case_id or f"CASE-{uuid.uuid4().hex[:12].upper()}"
            
            from decimal import Decimal
            values = {k: float(v) if isinstance(v, Decimal) else v for k, v in request.model_dump(mode="python").items()}
            
            row = connection.execute(
                """
                INSERT INTO corporate_credit_requests (
                    request_id, case_id, customer_id, submitted_by,
                    company_name, tax_id, legal_type, representative, industry,
                    business_scale, total_assets_billion_vnd,
                    net_revenue_billion_vnd, net_profit_billion_vnd,
                    debt_to_equity_ratio, cic_debt_classification,
                    current_debt_billion_vnd, collateral_description,
                    collateral_value_billion_vnd, casa_avg_balance_billion_vnd,
                    repayment_history, request_type, requested_amount_vnd,
                    requested_term_months, purpose, status, appraisal_status,
                    service_recommendation, service_recommendation_summary,
                    submission_idempotency_key, appraised_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 'WithRM', 'pending', ?, ?, ?, NULL,
                    CURRENT_TIMESTAMP
                )
                RETURNING *
                """,
                (
                    request_id, case_id, values["customer_id"], submitted_by,
                    values["company_name"], values["tax_id"], values["legal_type"],
                    values["representative"], values["industry"], values["business_scale"],
                    values["total_assets_billion_vnd"], values["net_revenue_billion_vnd"],
                    values["net_profit_billion_vnd"], values["debt_to_equity_ratio"],
                    values["cic_debt_classification"], values["current_debt_billion_vnd"],
                    values["collateral_description"], values["collateral_value_billion_vnd"],
                    values["casa_avg_balance_billion_vnd"], values["repayment_history"],
                    values["request_type"], values["requested_amount_vnd"],
                    values["requested_term_months"], values["purpose"],
                    Json(service_advisory["services"]), service_advisory["summary"],
                    idempotency_key,
                ),
            ).fetchone()
            return dict(row)

    def list_for_actor(
        self,
        *,
        submitted_by: str | None = None,
        customer_scope: Sequence[str] = (),
        status: str | None = None,
    ) -> List[Dict[str, Any]]:
        with pg.connect() as connection:
            if submitted_by:
                rows = connection.execute(
                    """SELECT * FROM corporate_credit_requests
                       WHERE submitted_by = ? ORDER BY submitted_at DESC""",
                    (submitted_by,),
                ).fetchall()
            elif customer_scope:
                placeholders = ",".join("?" for _ in customer_scope)
                if status:
                    rows = connection.execute(
                        f"""SELECT * FROM corporate_credit_requests
                           WHERE customer_id IN ({placeholders}) AND status = ?
                           ORDER BY submitted_at DESC""",
                        (*customer_scope, status),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        f"""SELECT * FROM corporate_credit_requests
                           WHERE customer_id IN ({placeholders}) ORDER BY submitted_at DESC""",
                        tuple(customer_scope),
                    ).fetchall()
            else:
                rows = []
            return [dict(row) for row in rows]

    def get(self, request_id: str) -> Dict[str, Any] | None:
        with pg.connect() as connection:
            row = connection.execute(
                "SELECT * FROM corporate_credit_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_by_case_id(self, case_id: str) -> List[Dict[str, Any]]:
        """Credit requests referencing this case_id. Used as a fallback
        access-scope check for case_ids that were auto-generated by create()
        (no prior intake, so no matching SharedCaseState row exists in
        `cases` -- see app/api/v2/workflow_router.py's _case_access())."""
        with pg.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM corporate_credit_requests WHERE case_id = ?",
                (case_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def forward(
        self,
        request_id: str,
        *,
        rm_id: str,
        rm_note: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        with pg.connect() as connection:
            replay = connection.execute(
                """SELECT * FROM corporate_credit_requests
                   WHERE forward_idempotency_key = ?""",
                (idempotency_key,),
            ).fetchone()
            if replay:
                if replay["request_id"] != request_id:
                    raise CreditRequestConflict("Idempotency key belongs to another request.")
                return dict(replay)

            row = connection.execute(
                """
                UPDATE corporate_credit_requests
                SET assigned_rm_id = ?, rm_note = ?, status = 'PendingAppraisal',
                    forward_idempotency_key = ?, forwarded_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE request_id = ? AND status = 'WithRM'
                RETURNING *
                """,
                (
                    rm_id, rm_note or None, idempotency_key, request_id,
                ),
            ).fetchone()
            if not row:
                raise CreditRequestConflict("Request is missing or not waiting for RM forward.")
            return dict(row)

    def appraise(
        self,
        request_id: str,
        *,
        expert_id: str,
        specialist_recommendation: str,
        specialist_reason: str,
        agent_appraisal: Dict[str, Any] | None,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        with pg.connect() as connection:
            replay = connection.execute(
                "SELECT * FROM corporate_credit_requests WHERE appraisal_idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if replay:
                if replay["request_id"] != request_id:
                    raise CreditRequestConflict("Idempotency key belongs to another request.")
                return dict(replay)

            needs_more = specialist_recommendation == "needs_more_information"
            row = connection.execute(
                """
                UPDATE corporate_credit_requests
                SET assigned_expert_id = ?, specialist_recommendation = ?,
                    specialist_reason = ?, appraisal_summary = ?,
                    appraisal_score = ?, agent_recommendation = ?,
                    appraisal_status = ?,
                    appraisal_idempotency_key = ?, appraised_at = CURRENT_TIMESTAMP,
                    status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE request_id = ? AND status = 'PendingAppraisal'
                RETURNING *
                """,
                (
                    expert_id, specialist_recommendation, specialist_reason,
                    agent_appraisal["summary"] if agent_appraisal else None,
                    agent_appraisal["score"] if agent_appraisal else None,
                    agent_appraisal["recommendation"] if agent_appraisal else None,
                    "needs_more_information" if needs_more else "completed",
                    idempotency_key, "WithRM" if needs_more else "PendingFinalApproval",
                    request_id,
                ),
            ).fetchone()
            if not row:
                raise CreditRequestConflict("Request is missing or not awaiting specialist appraisal.")
            return dict(row)

    def reopen_after_resubmission(self, request_id: str) -> Dict[str, Any] | None:
        """Customer resubmitting the requested document puts the request
        straight back in the Credit Specialist's queue -- it should not
        need a second manual RM forward for every round. Best-effort: if
        the request is not currently WithRM (e.g. already reopened by a
        concurrent call), this is a no-op and returns None rather than
        raising, since it is an automatic side effect, not a direct,
        idempotency-key-guarded user action."""
        with pg.connect() as connection:
            row = connection.execute(
                """
                UPDATE corporate_credit_requests
                SET status = 'PendingAppraisal', updated_at = CURRENT_TIMESTAMP
                WHERE request_id = ? AND status = 'WithRM'
                RETURNING *
                """,
                (request_id,),
            ).fetchone()
            return dict(row) if row else None

    def create_proposal(
        self,
        request_id: str,
        *,
        rm_id: str,
        note: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        with pg.connect() as connection:
            replay = connection.execute(
                "SELECT * FROM corporate_credit_requests WHERE proposal_idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if replay:
                if replay["request_id"] != request_id:
                    raise CreditRequestConflict("Idempotency key belongs to another request.")
                return dict(replay)

            row = connection.execute(
                """
                UPDATE corporate_credit_requests
                SET proposal_created_at = CURRENT_TIMESTAMP, proposal_created_by = ?,
                    proposal_note = ?, proposal_idempotency_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE request_id = ? AND status = 'PendingFinalApproval' AND proposal_created_at IS NULL
                RETURNING *
                """,
                (rm_id, note or None, idempotency_key, request_id),
            ).fetchone()
            if not row:
                raise CreditRequestConflict(
                    "Request is missing, not cleared by a specialist yet, or already has a proposal."
                )
            return dict(row)

    def decide(
        self,
        request_id: str,
        *,
        expert_id: str,
        decision: str,
        reason: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        with pg.connect() as connection:
            replay = connection.execute(
                """SELECT * FROM corporate_credit_requests
                   WHERE decision_idempotency_key = ?""",
                (idempotency_key,),
            ).fetchone()
            if replay:
                if replay["request_id"] != request_id:
                    raise CreditRequestConflict("Idempotency key belongs to another request.")
                return dict(replay)

            current = connection.execute(
                "SELECT proposal_created_at FROM corporate_credit_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if current is not None and not current["proposal_created_at"]:
                raise CreditRequestConflict(
                    "RM has not created a proposal for this request yet -- Manager cannot decide before that."
                )

            if decision == "needs_more_information":
                final_decision = None
                status = "PendingAppraisal"
                appraisal_status = "needs_more_information"
            else:
                final_decision = decision
                status = decision.title()
                appraisal_status = "completed"

            # Sending the request back to the specialist invalidates the
            # existing RM proposal -- create_proposal()'s guard requires
            # proposal_created_at IS NULL, so without resetting it here the
            # RM could never submit a second proposal after this round trip.
            reset_proposal = decision == "needs_more_information"

            row = connection.execute(
                f"""
                UPDATE corporate_credit_requests
                SET assigned_expert_id = ?, final_decision = ?, decision_reason = ?,
                    approved_by = ?, status = ?, appraisal_status = ?,
                    decision_idempotency_key = ?, decided_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                    {", proposal_created_at = NULL, proposal_created_by = NULL, "
                     "proposal_note = NULL, proposal_idempotency_key = NULL" if reset_proposal else ""}
                WHERE request_id = ? AND status = 'PendingFinalApproval'
                RETURNING *
                """,
                (
                    expert_id, final_decision, reason, expert_id, status,
                    appraisal_status, idempotency_key, request_id,
                ),
            ).fetchone()
            if not row:
                raise CreditRequestConflict("Request is missing or not awaiting final approval.")
            return dict(row)
