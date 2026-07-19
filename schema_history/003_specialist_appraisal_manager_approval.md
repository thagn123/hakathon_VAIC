# 003 — Specialist appraisal and Manager approval

- Migration: `scripts/migrations/003_specialist_appraisal_manager_approval.sql`
- Flow: `WithRM` → `PendingAppraisal` → `PendingFinalApproval` → `Approved|Rejected`
- Credit Specialist owns appraisal (`credit:appraise`).
- Manager owns final decision (`credit:final_approve`).
- Agent only suggests services and recommends whether to disburse.
- Customer API response excludes AI, specialist, RM and approval internals.

Rollback requires restoring the prior status constraint and role permissions;
do not rollback while rows are in either new pending status.
