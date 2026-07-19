-- Migration 002: Customer -> RM (agent #1) -> Credit Specialist (agent #2) -> customer.
-- Agent #1 stays at create (credit appraisal). Agent #2 runs at RM forward (service advisory).

ALTER TABLE corporate_credit_requests
    ADD COLUMN IF NOT EXISTS assigned_rm_id              VARCHAR(64),
    ADD COLUMN IF NOT EXISTS rm_note                     TEXT,
    ADD COLUMN IF NOT EXISTS forward_idempotency_key     VARCHAR(128),
    ADD COLUMN IF NOT EXISTS forwarded_at                TIMESTAMP,
    ADD COLUMN IF NOT EXISTS service_recommendation      JSONB,
    ADD COLUMN IF NOT EXISTS service_recommendation_summary TEXT,
    ADD COLUMN IF NOT EXISTS service_recommended_at      TIMESTAMP;

ALTER TABLE corporate_credit_requests
    DROP CONSTRAINT IF EXISTS corporate_credit_requests_status_check;

ALTER TABLE corporate_credit_requests
    ADD CONSTRAINT corporate_credit_requests_status_check
    CHECK (status IN ('WithRM', 'PendingApproval', 'Pending', 'Approved', 'Rejected'));

-- Existing Pending (pre-RM-gate) rows become WithRM so they enter the new queue.
UPDATE corporate_credit_requests
SET status = 'WithRM', updated_at = CURRENT_TIMESTAMP
WHERE status = 'Pending' AND final_decision IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_forward_key
    ON corporate_credit_requests(forward_idempotency_key)
    WHERE forward_idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_credit_requests_status
    ON corporate_credit_requests(status, submitted_at DESC);

UPDATE permissions
SET permissions = permissions || '["credit:forward"]'::jsonb
WHERE employee_id = 'RM-999'
  AND NOT permissions @> '["credit:forward"]'::jsonb;
