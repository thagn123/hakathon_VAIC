# 21 — P0 Integration Fixes

Phạm vi: toàn bộ hạng mục P0 trong prompt "P0 INTEGRATION COMPLETION" áp dụng cho **Credit Request pipeline** (pipeline duy nhất đã có luồng thật chạy qua browser theo báo cáo 17/18). Mục tiêu: biến `FINAL STATUS: PARTIALLY INTEGRATED` (báo cáo 17) thành một luồng đầy đủ, thật, chạy được qua UI: `Customer → RM → Credit Specialist → RM → Customer bổ sung hồ sơ → Evidence cập nhật → Credit Specialist review lại → RM tạo proposal → Manager approval`.

## 1. Ba bản sửa đã kiểm chứng trước đó — đã commit riêng

Commit `3c0c4d6` (`fix(credit-workflow): restore request enrichment and specialist approval permissions`) — đúng như báo cáo 17 mô tả, không gộp với thay đổi lần này.

## 2. Bảng artifact (file tạo/sửa trong lần P0 này)

| File | Loại | Mục đích | Nội dung chính |
| --- | --- | --- | --- |
| `app/storage/migrations.py` | Sửa | Thêm migration v3 | 4 bảng mới (`customer_document_requests`, `credit_request_review_rounds`, `timeline_events`, `notifications`) + 4 cột proposal trên `corporate_credit_requests` + index theo case/role/status/recipient |
| `app/storage/workflow_repository.py` | Mới | Data layer cho 4 bảng trên | `WorkflowRepository`: CRUD document-request, review-round (append-only), timeline event (append-only), notification |
| `app/storage/credit_request_repository.py` | Sửa | Thêm bước Proposal + tự mở lại vòng thẩm định | `create_proposal()` (gate bằng `proposal_created_at IS NULL`), `decide()` reset lại proposal khi Manager trả `needs_more_information`, `reopen_after_resubmission()` (WithRM→PendingAppraisal tự động khi khách bổ sung hồ sơ), `list_by_case_id()` |
| `app/schemas/v2/credit_request.py` | Sửa | Thêm `CreditProposalRequest`, thêm `requested_document_type` vào `CreditAppraisalRequest` | |
| `app/schemas/v2/specialist_review.py` | Sửa | Sửa RBAC bảo hiểm + thêm contract forward | `_REVIEWER_ROLES` bổ sung `INSURANCE_SPECIALIST`; `ForwardToSpecialistRequest` mới |
| `app/reliability/capability_registry.py` | Sửa | Thêm quyền mới cho RM | `credit:create_proposal` |
| `app/integrations/enterprise.py` | Sửa | Cấp quyền IAM thật cho RM-999 | `specialist_review:request` (đã có sẵn trong registry nhưng chưa từng được cấp — capability "mồ côi"), `credit:create_proposal` |
| `app/api/v2/credit_request_router.py` | Sửa | Nối toàn bộ side-effect thật vào 4 endpoint sẵn có + 1 endpoint mới | timeline event, document-request, review-round, notification, Next-Best-Work tại `create/forward/appraisal/decision`; endpoint mới `POST /credit-requests/{id}/proposal`; sửa bug ẩn `stored.state.customer` → `stored.state.context.customer` (xem mục 4) |
| `app/api/v2/employee_router.py` | Sửa | Endpoint RM forward-to-specialist thật | `POST /cases/{case_id}/forward-to-specialist` — tạo WorkItem thật + timeline + notification, KHÔNG đổi case status (khác hẳn `submit_specialist_review`) |
| `app/api/v2/workflow_router.py` | Mới | Toàn bộ API mới cho document-request/timeline/notification/queue động | `GET/POST /cases/{id}/document-requests`, `GET /customer/document-requests`, `GET /document-requests/{id}`, `POST /document-requests/{id}/submit`, `POST /document-requests/{id}/cancel`, `GET/POST /me/notifications`, `POST /notifications/{id}/read`, `GET /work-items/my` |
| `app/api/v2/router.py` | Sửa | Ghi timeline thật cho pipeline SalesCase (intake/analysis) | `CASE_CREATED`, `DOCUMENT_UPLOADED`, `PROFILE_CONFIRMED`, `AGENT_ANALYSIS_COMPLETED` |
| `app/main.py` | Sửa | Mount router mới | `workflow_router` |
| `app/static/app.js` | Sửa | Toàn bộ UI mới + 2 bug fix | Xem báo cáo 20 cũ (mục 1) đã sửa `d.name`→`d.filename`; `forwardToSpecialist()` viết lại hoàn toàn (form thật, không còn `prompt()`, không còn false-success); `loadSpecialistQueue()`/`viewSpecialistTask()` dùng `/work-items/my` thật; `loadCustomerDocRequests()` dùng API thật thay vì suy luận từ specialist-reviews; upload-thay-thế; notifications; tab Timeline; nút "Tạo Proposal" cho RM + gate hiển thị cho Manager |
| `app/static/index.html` | Sửa | DOM cho các panel mới | Dropdown bảo hiểm sửa `INS-001`→`SPEC-INSURANCE-001`; panel thông báo; panel "Hồ sơ cần bổ sung"; tab Timeline |
| `tests/unit/test_v2_employee_context.py`, `tests/unit/test_v2_storage_approval.py` | Sửa | Cập nhật 2 assertion cứng bị ảnh hưởng bởi thay đổi có chủ đích | Danh sách permission RM (+2 quyền mới), `LATEST_SCHEMA_VERSION` (2→3) |
| `tests/browser/test_full_cross_role_journey.py` | Viết lại hoàn toàn | E2E 19 bước theo đúng journey yêu cầu | Xem báo cáo 22 |

## 3. Quyết định thiết kế quan trọng (và lý do)

- **"RM tạo proposal" là bước gate thật, không phải cosmetic**: thêm cột `proposal_created_at/by/note/idempotency_key`; `decide()` (Manager) **từ chối cứng bằng 409** nếu chưa có proposal. Đã kiểm chứng bằng test âm tính (xem báo cáo 22).
- **Không tạo bảng `next_best_work_items` mới** — tái sử dụng `employee_work_items` đã có sẵn (đúng yêu cầu mục 14: "Nếu một số table đã tồn tại, tái sử dụng thay vì tạo bản sao"). Chỉ thêm cách phân biệt item thật/seed qua tiền tố `item_id` (`TASK-`=seed, `FORWARD-`/`CREDIT-NBW-`/`REVIEW-NOTIFY-`=thật), không sửa schema bảng.
- **Khách hàng bổ sung hồ sơ → tự động PendingAppraisal, không cần RM forward lại lần 2**: phát hiện trong lúc test rằng journey 19 bước của prompt không có bước "RM re-forward" giữa "customer resubmit" và "specialist review vòng 2" — sửa `submit_document_request` để tự chuyển trạng thái, đúng với thiết kế journey yêu cầu.
- **`forward-to-specialist` là endpoint hoàn toàn mới, không phải patch nút cũ**: nút RM cũ gọi nhầm endpoint `specialist-reviews` (endpoint của CHÍNH chuyên viên dùng để ra quyết định), gửi `findings` sai kiểu dữ liệu. Thay vì vá payload, đã tạo đúng hành động RM cần ("giao việc cho chuyên viên") — không đổi case status, chỉ tạo WorkItem + timeline + notification. Dùng capability `specialist_review:request` — capability này **đã tồn tại sẵn trong `capability_registry.py` từ trước nhưng chưa từng được cấp cho ai** (xác nhận bằng grep toàn repo, 0 chỗ dùng) — bằng chứng cho thấy đây đúng là chỗ trống được thiết kế sẵn nhưng chưa hoàn thiện.

## 4. Bug thật phát sinh trong lúc build P0 (không phải do cố tình tạo, được phát hiện và sửa ngay)

| # | File:dòng | Mô tả | Bằng chứng |
| - | --- | --- | --- |
| 1 | `credit_request_router.py:_enrich_with_sales_case` | `stored.state.customer` — `SharedCaseState` không có field `customer` ở top-level (đúng field là `stored.state.context.customer`). Lỗi này **ngủ yên từ trước tới giờ** vì chỉ kích hoạt khi `V2Repository.get_case()` trả về state thật (case đã chạy `run-analysis` ít nhất 1 lần) — không có test/journey nào trước đây từng chạy `run-analysis` xong rồi gọi `GET /credit-requests` trên cùng case. | Traceback đầy đủ trong `uvicorn.log`; xác nhận lại bằng cách restart server + chạy lại E2E — lỗi biến mất sau khi sửa 1 dòng |
| 2 | `credit_request_router.py:appraise_credit_request` (đã sửa trong session này) | Firing `WORK_ITEM_REOPENED` sai chỗ (ở vòng thẩm định thay vì ở đúng lúc khách hàng nộp lại hồ sơ) — đã dời sang `workflow_router.py:submit_document_request` cho đúng ngữ nghĩa "reopen" | Tự phát hiện khi review lại thiết kế, sửa trước khi chạy E2E |

Cả hai lỗi đã sửa và xác nhận lại bằng pytest (585 passed) + E2E pass hoàn chỉnh.

## 5. Bảng sản xuất-sẵn-sàng (theo khung AGENTS.md)

| Hạng mục | Đã có? | Ghi chú |
| --- | --- | --- |
| Data strategy | Có | 4 bảng mới qua migration có version-tracking, không phá dữ liệu cũ |
| Retrieval quality | N/A | Không áp dụng (không phải RAG) |
| Guardrails/HITL | Có | Proposal gate cứng bằng 409; customer_safe_reason tách biệt internal_reason; capability+role kép cho mọi endpoint mới |
| Evaluation | Một phần | 1 E2E 19 bước pass hoàn chỉnh (báo cáo 22); chưa có golden-set 20-50 case đa dạng theo AGENTS.md §7 |
| Observability | Có | `timeline_events` + `notifications` + `JsonEventLogger.emit` ở mọi endpoint mới |
| Reliability | Một phần | Idempotency-Key giữ nguyên cho các endpoint có sẵn + endpoint proposal mới; `reopen_after_resubmission` không cần idempotency-key vì là side-effect nội bộ có WHERE-guard tự nhiên |
| Security/privacy | Có | Xác nhận bằng test: `specialist_reason`/`specialist_recommendation`/`proposal_note` không lộ ra customer view |
