# SQL entity map

## `corporate_credit_requests`

Purpose: immutable-at-submission snapshot of the customer credit request plus
the latest appraisal/final-decision state.

- PK: `request_id`
- Customer link: `customer_id → companies.tax_id` (the referenced column stores
  the internal customer key such as `COMP-MP`)
- Customer tax number snapshot: `tax_id` (no FK)
- Submission actor: `submitted_by`
- Agent output: `appraisal_status`, `appraisal_score`,
  `agent_recommendation`, `appraisal_summary`
- Human decision: `assigned_expert_id`, `final_decision`, `decision_reason`,
  `approved_by`, `decided_at`
- Replay protection: unique submission and decision idempotency keys

Write path:

`Customer UI → POST /api/v2/credit-requests → deterministic appraisal → INSERT`

`Credit Specialist UI → POST /api/v2/credit-requests/{id}/decision → UPDATE`
