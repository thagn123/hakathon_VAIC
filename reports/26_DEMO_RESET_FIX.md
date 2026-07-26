# 26 — Demo Reset Fix (đúng database đang chạy, seed 1 case sạch)

## 1. Vấn đề đã xác nhận (báo cáo 17, mục "Rủi ro còn lại" #4)

`POST /api/v2/demo/reset` (`app/api/v2/demo_router.py`) trước đây tự mở một file SQLite
thứ hai, hard-code cứng đường dẫn:
```python
_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "mock_database" / "enterprise_core.sqlite3"
```
File này **chỉ chứa dữ liệu SSO/IAM** (bảng `employees`, `permissions`, `customers` — xem
`app/integrations/enterprise.py`). Toàn bộ dữ liệu nghiệp vụ thật (`cases`,
`corporate_credit_requests`, `intake_sessions`, `employee_work_items`,
`customer_document_requests`, `timeline_events`, `notifications`, ...) nằm ở một database
**hoàn toàn khác** — database mà `app/storage/pg.py` phân giải từ `settings.DATABASE_URL`
(Postgres nếu có) hoặc `settings.V2_DB_PATH` (SQLite cục bộ, `./data/state/v2.sqlite3`).

Hệ quả: mọi `DELETE FROM cases/intake_sessions/corporate_credit_requests/documents` trong
`reset_demo()` ném `sqlite3.OperationalError` (bảng không tồn tại trong file đó) và bị nuốt
lặng lẽ bằng `except sqlite3.OperationalError: pass`. **Endpoint chưa từng xoá được bất kỳ
dữ liệu thật nào** kể từ khi được viết. Xác nhận trực tiếp bằng SQL trước khi sửa: database
đang chạy có 56 `cases`, 22 `corporate_credit_requests`, 45 `notifications`, ... tích luỹ qua
nhiều lần chạy thử.

## 2. Cách sửa

`app/api/v2/demo_router.py` được viết lại hoàn toàn:

- **Không còn đường dẫn SQLite thứ hai nào bị hard-code.** Endpoint dùng đúng
  `app.storage.pg` — connection resolver DUY NHẤT mà mọi endpoint khác trong app dùng
  (`pg.connect()` → Postgres qua `DATABASE_URL` nếu có, ngược lại SQLite qua
  `settings.V2_DB_PATH`).
- Gọi `V2Repository(settings.V2_DB_PATH)` trước khi xoá — constructor của nó tạo mọi bảng
  còn thiếu (`cases`, `audit_events`, `approval_tokens`, `idempotency_records`,
  `metadata_*`, và chạy `apply_migrations()`), nên endpoint an toàn ngay cả khi gọi lần đầu
  tiên trên một file database hoàn toàn trống — **schema/migrations được bảo toàn, không
  bao giờ bị DROP**.
- Xoá 22 bảng dữ liệu demo theo đúng thứ tự phụ thuộc (con trước cha, khớp
  `FOREIGN KEY ... ON DELETE CASCADE` khai báo trong `migrations.py`):
  notifications → timeline_events → employee_work_items (Next-Best-Work) →
  credit_request_review_rounds + specialist_reviews → customer_document_requests →
  approval_tokens (approvals) → document_extractions/extracted_fields/field_conflicts/
  document_processing_jobs (evidence/document links) → case_documents (documents) →
  corporate_credit_requests (credit requests) → intake_sessions/customer_profile_drafts/
  cases/audit_events/idempotency_records/metadata_* (sales cases).
- **Không đụng vào** `schema_migrations`, và không đụng vào các bảng identity/config
  (`employee_personas`, `employee_preferences`, `employee_habits`, `employee_consent`,
  `employee_recommendation_feedback`, `operational_readiness`) — xoá các bảng này sẽ phá
  đăng nhập của phiên demo đang chạy, và chúng không phải "dữ liệu case", mà là cấu hình
  nhân sự/persona.
- Seed đúng 1 case tín dụng sạch bằng cách gọi thẳng
  `CreditRequestRepository().create(...)` + `CreditReadinessService().recommend_services(...)`
  — **cùng một code path** mà `POST /api/v2/credit-requests` (customer thật) dùng, không
  viết tay câu INSERT riêng — nên hàng vừa seed không thể phân biệt được với một case do
  khách hàng thật gửi. Dùng đúng persona demo có sẵn (`USER-MP-001` / `COMP-MP`, Công ty
  TNHH Minh Phát) đã được cấu hình sẵn trong `app/integrations/enterprise.py`.
- `POST /api/v2/demo/seed` (endpoint cũ, tách biệt) nay chỉ là alias gọi lại `reset_demo()`
  — trước đây nó chỉ set lại rồi yêu cầu người dùng tự bấm nút "Use Demo Data" trên UI,
  không thực sự tạo case nào.

## 3. Bằng chứng — chạy reset 2 lần liên tiếp, xác nhận idempotent bằng SQL

Trạng thái DB **trước khi sửa** (đọc trực tiếp bằng sqlite3, không qua endpoint cũ):

| Bảng | Số dòng trước | Sau reset lần 1 | Sau reset lần 2 |
| --- | ---: | ---: | ---: |
| cases | 56 | 0 | 0 |
| corporate_credit_requests | 22 | 1 | 1 |
| intake_sessions | 59 | 0 | 0 |
| notifications | 45 | 0 | 0 |
| timeline_events | 197 | 0 | 0 |
| employee_work_items | 32 | 0 | 0 |
| customer_document_requests | 8 | 0 | 0 |
| approval_tokens | 19 | 0 | 0 |
| (17 bảng còn lại trong danh sách) | (đều >0) | 0 | 0 |

Response thực tế của 2 lần gọi liên tiếp (`curl -X POST /api/v2/demo/reset`):
```
Lần 1: seeded_case = {"request_id": "CR-8B54D11E42A0", "case_id": "CASE-073E4E540D24", "status": "WithRM"}
Lần 2: seeded_case = {"request_id": "CR-22E40487A7C1", "case_id": "CASE-72F5D2F52979", "status": "WithRM"}
```
Sau lần 2, `corporate_credit_requests` có **đúng 1 dòng** — dòng của request `CR-8B54D11E42A0`
từ lần 1 đã bị xoá sạch trước khi lần 2 seed dòng mới. Đây là bằng chứng idempotent: gọi bao
nhiêu lần liên tiếp cũng luôn hội tụ về đúng 1 trạng thái sạch (1 case), không cộng dồn rác.
`employee_personas` giữ nguyên 7 dòng (đăng nhập không bị ảnh hưởng); `schema_migrations`
vẫn còn đủ 3 version (1, 2, 3) sau reset — schema không bị phá.

## 4. Chạy lại toàn bộ kiểm thử sau khi sửa

- **Pytest (toàn bộ, trừ `tests/browser`)**: `584 passed, 5 skipped` — 1 test
  (`tests/test_auth.py::test_tampered_session_token_is_rejected`) từng fail 1 lần khi chạy
  chung cả bộ nhưng **pass khi chạy riêng lẻ và pass ở lần chạy lại thứ 2 của cả bộ** — xác
  nhận đây là flaky test có sẵn (không liên quan tới thay đổi lần này, không đụng gì tới
  JWT/session), không phải regression.
- **Cross-role browser E2E 19 bước** (`tests/browser/test_full_cross_role_journey.py`),
  chạy ngay sau một lần `/api/v2/demo/reset` thật trên server vừa khởi động lại: **1 passed**,
  **0 console error, 0 HTTP ≥ 400** trên toàn bộ 31 mục trong `trace.json`. Test tự tạo case
  riêng của nó (không phụ thuộc case được seed bởi reset), nên không bị ảnh hưởng bởi case
  demo vừa seed — đúng như thiết kế test đã có từ báo cáo 22 (định vị theo `case_id` chính
  xác, miễn nhiễm với dữ liệu demo khác đang tồn tại).
- Phụ lục đáng chú ý: `step16_manager_dashboard` trong lần chạy này báo `total_cases_text: "1"`
  (chỉ còn case mà chính E2E test vừa tạo) — so với trước khi sửa, dashboard luôn hiện con số
  cộng dồn (ví dụ "56") do reset không hoạt động. Đây là bằng chứng gián tiếp cho thấy reset
  giờ hoạt động thật trên đúng database mà Manager Dashboard cũng đọc.

## 5. Giới hạn còn lại

- `POST /api/v2/demo/seed` giữ nguyên như một alias để không phá bất kỳ script/nơi gọi cũ nào
  (`scripts/run_demo_smoke.py` gọi cả `/reset` và `/seed` liên tiếp) — cả hai giờ cho cùng
  kết quả (reset + seed 1 case), không còn hành vi khác biệt như thiết kế cũ.
- Case được seed chỉ đi qua nhánh Credit Request (không có `intake_sessions`/`case_documents`
  đi kèm vì được tạo với `case_id=None`, giống cách `workflow_router.py:_case_access` đã hỗ
  trợ fallback từ trước cho các case chỉ có Credit Request mà chưa từng chạy `run-analysis`).
  Muốn seed một case đã intake/upload/phân tích đầy đủ cần gọi thêm chuỗi API intake — nằm
  ngoài yêu cầu "seed đúng 1 case tín dụng sạch" của lần sửa này.
- Bảng `companies` (khai báo trong migration nhưng không có endpoint nào đọc/ghi — xác nhận
  bằng grep toàn repo) được cố tình để ngoài danh sách xoá vì không phải dữ liệu demo theo
  case, chỉ là schema chết.

## 6. Artifact

| File | Loại | Mục đích | Nội dung chính |
| --- | --- | --- | --- |
| `app/api/v2/demo_router.py` | Sửa toàn bộ | Reset đúng database đang chạy + seed 1 case sạch | Dùng `app.storage.pg`/`settings.V2_DB_PATH` thay vì đường dẫn hard-code; xoá 22 bảng theo thứ tự phụ thuộc; seed qua `CreditRequestRepository.create()` thật |
| `reports/cross_role/*.png`, `reports/cross_role/trace.json` | Sinh lại | Bằng chứng E2E 19 bước chạy lại sau reset | Ảnh chụp + trace mới, không đổi kịch bản test |
