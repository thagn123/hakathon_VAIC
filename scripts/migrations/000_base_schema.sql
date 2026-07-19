-- Migration 000: consolidated base schema (bootstrap for a fresh PostgreSQL).
--
-- Consolidates the tables that migrations 001-003 assume already exist:
--   * companies                    (KYC snapshot; referenced by the FK below)
--   * corporate_credit_requests    (customer credit request + workflow state)
--
-- The table is written in its FINAL column shape (after 001-003), so on a fresh
-- database only this file is required. Migrations 001-003 remain safe to re-run
-- afterwards: every statement there is guarded by IF EXISTS / IF NOT EXISTS.
--
-- companies.tax_id here stores the internal customer key (e.g. COMP-MP), which
-- is why corporate_credit_requests.customer_id (not tax_id) carries the FK.
-- corporate_credit_requests.tax_id is the customer-supplied tax number snapshot
-- and deliberately has no FK.

-- ---------------------------------------------------------------------------
-- companies: minimal KYC row needed by the credit-request FK + seed scripts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    tax_id              VARCHAR(64) PRIMARY KEY,       -- internal customer key (COMP-*)
    company_name        VARCHAR(300) NOT NULL,
    established_date    DATE,
    legal_form          VARCHAR(200),
    registered_address  TEXT,
    business_address    TEXT
);

-- ---------------------------------------------------------------------------
-- corporate_credit_requests: immutable-at-submission snapshot + latest state.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corporate_credit_requests (
    -- Identity / linkage
    request_id                      VARCHAR(64) PRIMARY KEY,
    case_id                         VARCHAR(64),
    customer_id                     VARCHAR(64),        -- FK -> companies.tax_id
    submitted_by                    VARCHAR(64),

    -- Company snapshot (customer-supplied at submission)
    company_name                    VARCHAR(300),
    tax_id                          VARCHAR(30),        -- MST snapshot, no FK
    legal_type                      VARCHAR(100),       -- Loai hinh phap ly
    representative                  VARCHAR(200),       -- Nguoi dai dien
    industry                        VARCHAR(300),       -- Nganh nghe chinh (VSIC)
    business_scale                  VARCHAR(300),       -- Quy mo nhan su / nha may

    -- Financials
    total_assets_billion_vnd        NUMERIC,            -- Tong tai san (ty VND)
    net_revenue_billion_vnd         NUMERIC,            -- Doanh thu thuan (ty VND)
    net_profit_billion_vnd          NUMERIC,            -- Loi nhuan sau thue (ty VND)
    debt_to_equity_ratio            NUMERIC,
    cic_debt_classification         VARCHAR(100),
    current_debt_billion_vnd        NUMERIC,            -- Du no hien tai (ty VND)
    collateral_description          VARCHAR(300),       -- Tai san dam bao
    collateral_value_billion_vnd    NUMERIC,
    casa_avg_balance_billion_vnd    NUMERIC,
    repayment_history               VARCHAR(100),       -- Lich su tra no

    -- Request
    request_type                    VARCHAR(50),        -- loan | service | both
    requested_amount_vnd            NUMERIC,
    requested_term_months           INTEGER,
    purpose                         TEXT,

    -- Workflow status: Customer -> RM -> Credit Specialist -> Manager
    status                          VARCHAR(32) NOT NULL DEFAULT 'WithRM',

    -- RM handoff + Agent #2 service advisory (migration 002)
    assigned_rm_id                  VARCHAR(64),
    rm_note                         TEXT,
    forward_idempotency_key         VARCHAR(128),
    forwarded_at                    TIMESTAMP,
    service_recommendation          JSONB,
    service_recommendation_summary  TEXT,
    service_recommended_at          TIMESTAMP,

    -- Specialist appraisal (migrations 001 + 003)
    assigned_expert_id              VARCHAR(64),
    appraisal_status                VARCHAR(32) DEFAULT 'pending',
    appraisal_summary               TEXT,
    appraisal_score                 NUMERIC,
    agent_recommendation            VARCHAR(32),
    specialist_recommendation       VARCHAR(32),
    specialist_reason               TEXT,
    appraisal_idempotency_key       VARCHAR(128),

    -- Manager final decision (migration 001)
    final_decision                  VARCHAR(32),
    decision_reason                 TEXT,
    approved_by                     VARCHAR(64),

    -- Replay protection + timestamps
    submission_idempotency_key      VARCHAR(128),
    decision_idempotency_key        VARCHAR(128),
    submitted_at                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    appraised_at                    TIMESTAMP,
    decided_at                      TIMESTAMP,
    updated_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT corporate_credit_requests_status_check
        CHECK (status IN (
            'WithRM', 'PendingAppraisal', 'PendingFinalApproval',
            'Approved', 'Rejected'
        ))
);

-- Customer FK: guarded so re-running against an already-linked table is a no-op.
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

-- Lookup indexes
CREATE INDEX IF NOT EXISTS idx_credit_requests_customer
    ON corporate_credit_requests(customer_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_requests_appraisal
    ON corporate_credit_requests(appraisal_status, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_requests_status
    ON corporate_credit_requests(status, submitted_at DESC);

-- Idempotency uniqueness (partial: only when the key is present)
CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_submission_key
    ON corporate_credit_requests(submitted_by, submission_idempotency_key)
    WHERE submission_idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_forward_key
    ON corporate_credit_requests(forward_idempotency_key)
    WHERE forward_idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_appraisal_key
    ON corporate_credit_requests(appraisal_idempotency_key)
    WHERE appraisal_idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_requests_decision_key
    ON corporate_credit_requests(decision_idempotency_key)
    WHERE decision_idempotency_key IS NOT NULL;
