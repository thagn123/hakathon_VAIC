# 001 — Corporate credit request workflow

- Date: 2026-07-19
- Migration: `scripts/migrations/001_extend_credit_requests.sql`
- Applied: PostgreSQL configured by `DATABASE_URL`

Changes:

- Expanded `corporate_credit_requests` with full customer-form snapshot fields.
- Moved the company FK from customer tax number to internal `customer_id`.
- Added Agent appraisal and Credit Specialist final-decision fields.
- Added lookup and idempotency indexes.
- Granted `credit:final_approve` to the synthetic Credit Specialist persona.

Rollback is intentionally manual because removing snapshot/decision columns
would destroy audit data.
