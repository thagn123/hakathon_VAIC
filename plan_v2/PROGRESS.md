# PROGRESS — V2 Build State

## Tổng quan

| Trường | Giá trị |
|---|---|
| Plan version | `2.0.0` |
| Cập nhật cuối | `2026-07-18` |
| Giai đoạn | `Local/sandbox MVP complete; production integration pending` |
| Test/eval | `275 tests`; `40 business + 25 security + 20 reliability cases` |
| API | `39 /api/v2 routes`; `19` public sales-case facade routes |
| Blocker production | Thiếu data/API/SSO-IAM/policy owner/security sign-off thật |

`Done` trong bảng dưới đây chỉ có nghĩa hoàn thành acceptance ở phạm vi **synthetic local MVP**. Không đồng nghĩa production verified.

## Task tracker

| ID | Task | Status | Evidence chính | Deviation/giới hạn |
|---|---|---|---|---|
| V2-001 | Contracts + schema validation | Done | `app/schemas/v2`, intake/planner/shared-state/AI-log contracts, `tests/contract` | JSON schemas vẫn đóng gói dưới `plan_v2/contracts` |
| V2-002 | Employee/Workspace Context | Done | `app/context`, adapter/RBAC/provenance tests | Mock adapters |
| V2-003 | Context Assembler | Done | merge/conflict/minimize + resilient CRM tests | Chưa chạy trên enterprise gateway |
| V2-004 | Intent Extractor | Done | `app/intent`, intent/message-rerun tests | LLM optional; deterministic mặc định |
| V2-005 | Slot Auto-Fill + Confidence | Done | slot/confidence/clarification tests | Calibration mới trên synthetic set |
| V2-006 | Product ingestion/index | Done | Source Cards, byte parsers, governed ingestion, SQLite index | PDF scan cần OCR; Gold là synthetic |
| V2-007 | Hybrid retrieval/evidence | Done | Product service, ACL/version tests, golden eval | Dense layer là hash fallback |
| V2-008 | Eligibility/Legal | Done | rule registry + persistent Legal RAG + scope/evidence tests | Chưa có legal corpus/KYC-CIC thật |
| V2-009 | Orchestration/state machine | Done | state machine, DAG, impact/message resume tests | Single-process engine |
| V2-010 | Operations/dedup/resume | Done | checklist/artifact/dedup tests | CRM/task lookup là local draft/existing input |
| V2-011 | Safety/approval/executor | Done | injection quarantine, one-time token, payload hash, idempotency | Enterprise SoD chưa có |
| V2-012 | Storage/observability | Done | schema v2, intake persistence, quick-check, audit chain, per-case AI Decision Log, metrics/reliability | Backend local, chưa HA/OpenTelemetry/SIEM/retention production |
| V2-013 | API/UI | Done | 39 routes, 19-route sales facade, guided RM Workspace, AI log tab, browser E2E | Auth header synthetic; chưa formal accessibility audit |
| V2-014 | Evaluation/golden datasets | Done | 40 business + 25 security + 20 reliability cases, executable reports | Chưa có de-identified real data |
| V2-015 | E2E hardening | Done | 172 tests, prior 92% app coverage, intake→profile→analysis→approval→execute browser journey | Done cho sandbox; production checklist còn mở |
| V2-016 | Independent RAG MCP server | Done | Official MCP client/server transport, 4 tools, persistent 3-source/19-chunk index, ACL/auth/audit tests | Hash embedding + SQLite + synthetic corpus; production backend/auth/data còn mở |
| V2-017 | Complexity Router + Risk & Guardrail Gate as named components | Done | `app/workflow/router.py` (`ComplexityRouter`), `app/workflow/risk_gate.py` (`RiskGuardrailGate`), `risk_gate_result` in `SharedCaseState`/JSON contract, `tests/unit/test_v2_risk_gate_and_router.py`, `docs/SHB_MULTI_AGENT_WORKFLOW_DIAGRAM_MAPPING.md` | Product/Compliance/Operations stay sequential by design (Compliance genuinely needs Product's product_ids first — see mapping doc section 3); this is a scoped, spec-aligned deviation from a literal reading of the diagram's parallel boxes, not an oversight |
| V2-018–025 | Intelligent Expert Agent collaboration upgrade | Done cho synthetic local MVP | LangGraph Product/Credit/Insurance, immutable manifests, exact tool allowlist, typed findings/synthesis, Agent Knowledge Console, AI Decision Log và E2E approval/execute tests | LLM/MCP thật, dữ liệu thật và security sign-off production vẫn chưa có; Legal/Eligibility và Operations giữ deterministic |
| V2-026 | Customer credit request → Agent appraisal → Credit Specialist final decision | Done cho synthetic local MVP | PostgreSQL migration, `/api/v2/credit-requests`, Customer form, Credit Specialist approval queue, appraisal/unit/API smoke tests | Agent appraisal là deterministic screening; chưa thay thế underwriting/risk policy thật |
| V2-027 | RM forward gate + second agent (service advisory) | Done cho synthetic local MVP | Migration 002, `WithRM`→`PendingApproval`, `POST /forward`, RM UI queue, service recommend unit + API smoke | Service advisory rule-based; chưa tick chọn dịch vụ khi approve |
| V2-028 | Agent #2 dùng LLM thật (Gemini) có allowlist + fallback rule | Done cho synthetic local MVP | `app/credit/service_advisory_llm.py` tái dùng `BaseExpertRuntime`, `GOOGLE_MODEL=gemini-2.5-flash`, prefix `[AI:Gemini]`/`[Rule]`, API smoke `source=llm` | LLM chỉ chọn trong catalog cố định; key nằm ở `.env`; chưa có eval faithfulness |
| V2-029 | Tách thẩm định và phê duyệt cuối theo SoD | Done cho synthetic local MVP | Customer response whitelist; `POST /appraisal` cho Credit Specialist; `POST /decision` cho Manager; migration 003; smoke flow 4 vai trò | Agent chỉ khuyến nghị giải ngân; policy/risk model vẫn synthetic, chưa phải quyết định tín dụng production |
| V2-030 | Khách hàng tự tạo hồ sơ demo | Done cho local/sandbox | `POST /api/v2/auth/customer-users`, form tạo hồ sơ tại màn hình đăng nhập, CRM context tự điền Customer form, `tests/test_auth.py` | Chỉ bật cùng demo auth; dùng mật khẩu demo chung, chưa thay thế onboarding/KYC/SSO thật |

## Decision log

- Workflow-first, agent optional: LLM chỉ xử lý semantic extraction; business rule và external action deterministic.
- Contract-first: shared state/intent/context dùng V2 Pydantic + JSON Schema.
- Synthetic source phải có Source Card và không được trộn với production.
- Legal RAG cung cấp evidence; Eligibility Engine là nơi duy nhất quyết định pass/fail.
- Eligibility fail-closed; Product module luôn để `eligibility=unknown`.
- Approval gắn exact payload hash và one-time token; executor idempotent.
- SQLite được chọn cho MVP chạy ngay; repository port cho phép thay PostgreSQL khi pilot.
- AI Decision Log và Audit Log tách trách nhiệm: AI log giải thích model/rule/retrieval; audit log bất biến ghi actor/action. Cả hai đều gắn `case_id`/`trace_id`.
- AI log chỉ lưu output summary và source metadata đã sanitize; không lưu raw PII, secret, raw prompt hoặc approval token.
- RAG MCP tách process và chỉ expose read tools. Ingestion nằm ở Data Steward CLI, không cho LLM tự ghi serving index.
- MCP retrieval audit chỉ lưu caller/query hash và metadata vận hành; raw query/chunk/token không được ghi.
- Expert Agent không được yêu cầu hoặc lưu Chain-of-Thought; chỉ lưu decision rationale summary, facts/inferences/unknowns và evidence refs đã sanitize.
- Agent role/tool permission do immutable manifest + trusted runtime identity quyết định; system prompt không phải authorization boundary.
- Collaboration đi qua Coordinator bằng typed message; hard rule, Evidence Validator, Risk Gate và Approval không bị LLM/Coordinator override.
- Credit request Agent chỉ đưa khuyến nghị có giải thích; từ V2-029, `credit:appraise` thuộc Credit Specialist và `credit:final_approve` thuộc Manager để tách người thẩm định khỏi người quyết định cuối. Cả hai bước luôn yêu cầu thao tác UI/API rõ ràng cùng lý do.

## Verification log

- Chi tiết từng change set và lệnh kiểm tra: `docs/BUILD_V2_LOG.md`.
- Điểm readiness và gap production: `docs/V2_READINESS_REPORT.md`.
- Business eval: `data/eval/v2/latest_report.json`.
- Security/reliability eval: `data/eval/v2/latest_safety_reliability_report.json`.
- V2-030: `python -m pytest tests/test_auth.py -q` → 4 passed; `python -m pytest tests/test_api_v2.py -q` → 13 passed; `ruff check` và `node --check` pass.
