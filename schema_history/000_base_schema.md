# 000 — Base schema (bootstrap)

- Date: 2026-07-19
- Migration: `scripts/migrations/000_base_schema.sql`
- Applied: PostgreSQL configured by `DATABASE_URL`

Changes:

- Added the previously-missing base `CREATE TABLE` for `companies` and
  `corporate_credit_requests`. Migrations `001`–`003` only `ALTER` these tables,
  so a fresh database had no way to bootstrap them.
- `corporate_credit_requests` is written in its final column shape (after
  `001`–`003`), including the `status` CHECK, the `customer_id → companies.tax_id`
  FK, and all lookup / idempotency indexes.

Ordering: run `000` first. Migrations `001`–`003` stay safe to re-run afterwards
because every statement there is guarded by `IF EXISTS` / `IF NOT EXISTS`.

Rollback is intentionally manual: dropping these tables would destroy the
credit-request audit trail.
