# 002 — RM forward + second agent (service recommendation)

- Date: 2026-07-19
- Migration: `scripts/migrations/002_rm_forward_service_recommend.sql`
- Applied: PostgreSQL configured by `DATABASE_URL`

Changes:

- Inserted RM gate: `WithRM` → forward → `PendingApproval` → final decision.
- Agent #1 (credit appraisal) remains at customer submit; Agent #2 (service advisory) runs when RM forwards.
- Added `assigned_rm_id`, `rm_note`, forward idempotency, and `service_recommendation` JSONB.
- Expanded status CHECK to include `WithRM` / `PendingApproval`.
- Granted `credit:forward` to synthetic RM persona `RM-999`.
- Migrated open `Pending` rows to `WithRM`.

Rollback is manual: dropping service/RM columns would destroy handoff audit data.
