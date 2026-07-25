# 00_REPOSITORY_BASELINE

## 1. Git Status & Repository State
- **Branch**: `main` (up to date with `origin/main`)
- **Remote**: `https://github.com/thagn123/hakathon_VAIC`
- **Recent Commit**: `4ae22b7 feat: Nối luồng dữ liệu Sales Case và Credit Request xuyên suốt các Role`
- **Untracked files**:
  - `data/bo_ho_so_*`
  - `data/mau_ho_so_*`
  - `graphify-out/`
  - `scratch/*`

## 2. Architecture & Frameworks
- **Backend**: Python (FastAPI), running via `uvicorn`.
- **Frontend**: Vanilla HTML/JS/CSS (`app/static/index.html`, `app.js`, `app.css`).
- **Database**: SQLite (`data/mock_database/enterprise_core.sqlite3`) and possibly PostgreSQL depending on environment (`app/storage/pg.py`, `migrations.py`).
- **AI Workflow**: LangGraph/Custom Agent orchestration for multi-agent (Product Agent, Legal/Policy Agent, Operations Agent).
- **RAG/Embedding Provider**: Gemini/Vertex AI, with a fallback configuration (`AGENTIC_LLM_ENABLED` flag).

## 3. What is working
- Backend starts successfully via `uvicorn app.main:app`.
- Basic static UI serves at `http://localhost:8000/`.
- The Sales Case (Intake) workflow partially works: Customer uploads documents -> Extracts AI profile.
- Credit Request workflow recently linked: Credit form submissions now carry over `case_id` and attach Customer's uploaded documents and AI Profile to RM/Specialist/Manager views.
- SQLite database correctly handles basic CRUD for cases and credit requests.

## 4. What is failing / Missing
- **Demo Scenario**: Currently, the system does not have a deterministic "1-click seed" for the specific "Công ty Cổ phần Minh Phát" scenario requiring Payroll & Cash Management, with fake documents showing a missing UBO.
- **Workflow Completeness**:
  - The UI does not clearly show Evidence checklists with required statuses (`EXPLORATORY`, `CONDITIONAL`, `EVIDENCE_SUPPORTED`, `NOT_SUPPORTED`, `NEED_REVIEW`).
  - Agent outputs lack clear traceability to source documents (missing a unified `Evidence Validator` step that highlights missing info explicitly on UI).
  - Next Best Work (NBW) is somewhat implemented but needs to be tied cleanly to the final RM approval.
  - The "Trace" (AI Log) is available but might be too technical/JSON-heavy for a demo video.
- **Robustness**: 
  - Need a `/api/demo/reset` and `/api/demo/seed` to ensure repeatable demo runs without DB overlap.
  - No explicit fallback mode for AI endpoints if no API key is provided (currently it might just fail with 500).
- **Startup Script**: No `start_demo.ps1` or `start_demo.sh`.

## 5. Blockers & Risks
- **Risk**: AI might generate unpredictable results during the video recording if not properly constrained or seeded with deterministic fallback data.
- **Risk**: API rate limits or missing credentials for Gemini could crash the demo. Must ensure `DEMO FALLBACK` mock mode is rock-solid.
- **Blocker**: The UI needs a polished "DEMO MODE — SYNTHETIC DATA" banner and a "Reset Demo" button to satisfy the prompt's requirements.

## 6. Next Steps
Move to `reports/01_IMPLEMENTATION_PLAN.md` to break down the tasks into achievable steps.
