-- Migration 001: snapshot đầy đủ + workflow 3 vai trò cho yêu cầu tín dụng.
-- Customer submit -> Agent appraisal -> Credit Specialist final decision.
--
-- companies.tax_id hiện chứa mã khách hàng nội bộ (vd. COMP-MP), không phải
-- MST doanh nghiệp. Vì vậy customer_id mới giữ FK; tax_id trên request là MST
-- snapshot do khách hàng cung cấp.

ALTER TABLE corporate_credit_requests
    DROP CONSTRAINT IF EXISTS corporate_credit_requests_tax_id_fkey;

ALTER TABLE corporate_credit_requests
    ADD COLUMN IF NOT EXISTS customer_id              VARCHAR(64),
    ADD COLUMN IF NOT EXISTS case_id                  VARCHAR(64),
    ADD COLUMN IF NOT EXISTS submitted_by             VARCHAR(64),
    ADD COLUMN IF NOT EXISTS assigned_expert_id       VARCHAR(64),
    ADD COLUMN IF NOT EXISTS legal_type               VARCHAR(100),   -- Loại hình pháp lý
    ADD COLUMN IF NOT EXISTS representative           VARCHAR(200),   -- Người đại diện
    ADD COLUMN IF NOT EXISTS industry                 VARCHAR(300),   -- Ngành nghề chính (VSIC)
    ADD COLUMN IF NOT EXISTS business_scale           VARCHAR(300),   -- Quy mô nhân sự/nhà máy
    ADD COLUMN IF NOT EXISTS total_assets_billion_vnd     NUMERIC,    -- Tổng tài sản (tỷ VND)
    ADD COLUMN IF NOT EXISTS net_revenue_billion_vnd      NUMERIC,    -- Doanh thu thuần (tỷ VND)
    ADD COLUMN IF NOT EXISTS net_profit_billion_vnd       NUMERIC,    -- Lợi nhuận sau thuế (tỷ VND)
    ADD COLUMN IF NOT EXISTS current_debt_billion_vnd     NUMERIC,    -- Dư nợ hiện tại (tỷ VND)
    ADD COLUMN IF NOT EXISTS collateral_description   VARCHAR(300),   -- Tên tài sản đảm bảo
    ADD COLUMN IF NOT EXISTS repayment_history        VARCHAR(100),   -- Lịch sử trả nợ
    ADD COLUMN IF NOT EXISTS request_type             VARCHAR(50),    -- loan | service | both
    ADD COLUMN IF NOT EXISTS appraisal_status         VARCHAR(32) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS appraisal_summary        TEXT,
    ADD COLUMN IF NOT EXISTS appraisal_score          NUMERIC,
    ADD COLUMN IF NOT EXISTS agent_recommendation     VARCHAR(32),
    ADD COLUMN IF NOT EXISTS final_decision            VARCHAR(32),
    ADD COLUMN IF NOT EXISTS decision_reason           TEXT,
    ADD COLUMN IF NOT EXISTS approved_by               VARCHAR(64),
    ADD COLUMN IF NOT EXISTS submission_idempotency_key VARCHAR(128),
    ADD COLUMN IF NOT EXISTS decision_idempotency_key   VARCHAR(128),
    ADD COLUMN IF NOT EXISTS submitted_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS appraised_at              TIMESTAMP,
    ADD COLUMN IF NOT EXISTS decided_at                TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'corporate_credit_requests_customer_id_fkey'
    ) THEN
        ALTER TABLE corporate_credit_requests
            ADD CONSTRAINT corporate_credit_requests_customer_id_fkey
            FOREIGN KEY (customer_id) REFERENCES companies(tax_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_credit_requests_customer
    ON corporate_credit_requests(customer_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_requests_appraisal
    ON corporate_credit_requests(appraisal_status, submitted_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_submission_key
    ON corporate_credit_requests(submitted_by, submission_idempotency_key)
    WHERE submission_idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_decision_key
    ON corporate_credit_requests(decision_idempotency_key)
    WHERE decision_idempotency_key IS NOT NULL;

UPDATE permissions
SET permissions = permissions || '["credit:final_approve"]'::jsonb
WHERE employee_id = 'SPEC-CREDIT-001'
  AND NOT permissions @> '["credit:final_approve"]'::jsonb;
