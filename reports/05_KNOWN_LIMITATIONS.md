# 05_KNOWN_LIMITATIONS

## 1. Non-critical
- **Extracted Profile GET endpoint** (`/api/v2/sales-cases/{case_id}/profile`) returns 404. Profile data is already in the intake response payloads (steps 3, 5, 7). Impact: cosmetic only.
- **Agent fallback text is generic**: When `AGENTIC_LLM_ENABLED=false`, the `decision_rationale_summary` says "Fallback: LLM is disabled. Using static rules." For a more polished demo, you could set `AGENTIC_LLM_ENABLED=true` with a valid Gemini API key.

## 2. Demo-scope only
- **Mock PDF content**: The E2E test generates valid PDF structure but with minimal text. Document extraction/classification works but extracts limited fields from these minimal PDFs.
- **No real UBO verification**: The demo uses `ubo_status: "verified"` from CRM seed. In production this would be a real verification step.
- **Single customer scenario**: Only "Công ty Minh Phát" (COMP-MP) is fully seeded. Other customers (COMP-ABC, COMP-XYZ) exist in CRM but don't have the same depth of demo data.

## 3. Not implemented (out of scope for demo)
- **Specialist review workflow**: Specialist (SPEC-CREDIT-001) can view but the review/approval UI is not fully wired
- **Manager dashboard**: MGR-HN-01 sees aggregate view but detailed approval gate is not completed
- **Real document OCR**: Tesseract OCR is optional and not needed for demo
- **Email notifications**: No email/webhook integrations
- **PostgreSQL mode**: Demo uses SQLite only; PostgreSQL mode (`DATABASE_URL`) is untested in this demo cycle
