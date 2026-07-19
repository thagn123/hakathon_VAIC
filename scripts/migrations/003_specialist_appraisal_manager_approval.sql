-- Customer form -> Agent service suggestion -> RM -> Credit Specialist appraisal
-- -> Agent disbursement recommendation -> Manager final approval.

ALTER TABLE corporate_credit_requests
    ADD COLUMN IF NOT EXISTS specialist_recommendation VARCHAR(32),
    ADD COLUMN IF NOT EXISTS specialist_reason         TEXT,
    ADD COLUMN IF NOT EXISTS appraisal_idempotency_key VARCHAR(128);

ALTER TABLE corporate_credit_requests
    DROP CONSTRAINT IF EXISTS corporate_credit_requests_status_check;

-- Requests already waiting for the former final approver now enter appraisal.
UPDATE corporate_credit_requests
SET status = 'PendingAppraisal', updated_at = CURRENT_TIMESTAMP
WHERE status = 'PendingApproval' AND final_decision IS NULL;

ALTER TABLE corporate_credit_requests
    ADD CONSTRAINT corporate_credit_requests_status_check
    CHECK (status IN (
        'WithRM', 'PendingAppraisal', 'PendingFinalApproval',
        'Approved', 'Rejected'
    ));

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_appraisal_key
    ON corporate_credit_requests(appraisal_idempotency_key)
    WHERE appraisal_idempotency_key IS NOT NULL;

UPDATE permissions
SET permissions = (permissions - 'credit:final_approve') || '["credit:appraise"]'::jsonb
WHERE employee_id = 'SPEC-CREDIT-001';

UPDATE permissions
SET permissions = permissions || '["credit:final_approve"]'::jsonb
WHERE employee_id = 'MGR-HN-01'
  AND NOT permissions @> '["credit:final_approve"]'::jsonb;
