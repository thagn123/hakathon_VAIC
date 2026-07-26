# 17 — Cross-Role Reality Check (SHB Corporate Sales Copilot)

Ngày chạy: 2026-07-26
Commit tại thời điểm bắt đầu: `527e26f` (working tree). Trong lúc kiểm chứng, 4 commit khác (`dd19013`..`1a3f2db`, chỉ đổi `vercel.json`/`runtime.txt`/`api/index.py`/`app/config.py` Vercel path override) xuất hiện trên `main` từ một tiến trình khác — không đụng tới bất kỳ file nào liên quan tới luồng cross-role. Không ảnh hưởng tới kết quả bên dưới.
Phương pháp: đọc mã nguồn trực tiếp (không tin báo cáo cũ) + chạy server thật (`uvicorn`, SQLite `data/state/v2.sqlite3` + `data/mock_database/enterprise_core.sqlite3`) + Playwright Chromium (headless) điều khiển UI thật qua `tests/browser/test_full_cross_role_journey.py` + xác minh chéo bằng SQL trực tiếp và gọi API (chỉ dùng cho debug, không thay thế thao tác UI).

**Không có gì trong báo cáo này được suy luận — mọi khẳng định đều có bằng chứng: đường dẫn file:dòng, lệnh SQL, response HTTP, hoặc ảnh chụp màn hình trong `reports/cross_role/`.**

---

## 0. Ba bug chặn toàn bộ luồng đã tìm thấy và đã sửa

Trước khi làm được bất kỳ bước nào trong checklist, 3 bug sau **chặn cứng** toàn bộ luồng Credit Request đa vai trò. Không sửa thì không thể tiến hành reality check theo đúng yêu cầu ("chạy trực tiếp qua browser"). Cả ba đều là lỗi cấu hình/import cơ học, có bằng chứng rõ ràng (traceback, DB row), không phải suy đoán:

| # | File:dòng | Lỗi | Bằng chứng | Fix áp dụng |
|---|---|---|---|---|
| 1 | `app/api/v2/credit_request_router.py:151-153` (trước fix) | `from app.storage.repository import repo` và `from app.api.v2.intake_service import intake_service` — cả hai tên đều **không tồn tại** ở module scope (chỉ là closure riêng của `create_router()` trong `router.py`). Mọi gọi `GET /api/v2/credit-requests` hoặc `GET /api/v2/credit-requests/{id}` bởi RM/Credit Specialist/Manager → `ImportError` → 500 không điều kiện. | Traceback đầy đủ chạy `uvicorn --log-level debug`: `ImportError: cannot import name 'repo' from 'app.storage.repository'` tại `credit_request_router.py:152`. Xác nhận bug có từ commit `4ae22b7` (`git log -S"from app.storage.repository import repo"`). | Thay bằng `V2Repository(settings.V2_DB_PATH)` + `IntakeService(repository)` — đúng pattern đã dùng ở `app/api/v2/router.py:336-364` và `app/api/v2/employee_router.py:136-144`. Verify: `curl GET /api/v2/credit-requests` → 200, trả đủ dữ liệu thật. |
| 2 | `app/integrations/enterprise.py:147-149` (trước fix) | `_EMPLOYEE_COPILOT_DEMO_PERSONAS` cho `SPEC-CREDIT-001` thiếu quyền `credit:appraise`. `ensure_employee_copilot_demo_personas()` chạy **không điều kiện ở mọi lần start process** (gọi tại import-time của `employee_router.py`) và UPSERT đè quyền — nên Credit Specialist **không bao giờ** gọi được `POST /credit-requests/{id}/appraisal` dù server mới khởi động lại bao nhiêu lần. | `curl` trực tiếp DB `enterprise_core.sqlite3` bảng `permissions` cho `SPEC-CREDIT-001` → thiếu `credit:appraise`. Browser thật: click "Yêu cầu RM bổ sung" → console `403 POST .../appraisal`. | Thêm `credit:appraise` vào list. Verify: sau restart, DB có đủ quyền; browser thật click lại → 200, DB `specialist_recommendation="needs_more_information"` được ghi. |
| 3 | `app/integrations/enterprise.py:159-160` (trước fix) | Cùng lớp bug: `MGR-HN-01` thiếu `credit:final_approve` trong **chính danh sách trên** (trong khi bảng `employee_db.py` — không còn là nguồn thẩm quyền — lại có sẵn quyền này, gây ảo giác "chắc đã có"). | Browser thật: Manager điền lý do, bấm "Phê duyệt giải ngân" → console `403 POST .../decision`. | Thêm `credit:final_approve`. Verify: browser thật bấm lại → 200, DB `status="Approved"`, `final_decision="approved"`, `approved_by="MGR-HN-01"`. |

**Vì sao đáng nói cụ thể:** bug #2 và #3 là cùng một lỗi lặp lại hai lần — danh sách quyền "demo persona" ở `enterprise.py` (nguồn thẩm quyền IAM thật, theo đúng header docstring P0-fix của `employee_router.py`) không được cập nhật khi các endpoint `/appraisal` và `/decision` được thêm yêu cầu quyền mới, trong khi bảng cũ `employee_db.py` (không còn dùng để check quyền) lại "trông có vẻ đúng hơn". Đây chính xác là kiểu gap "trông như đã xong nhưng chưa" mà prompt yêu cầu phải lật ra.

Tất cả 3 file đã sửa đang ở trạng thái **uncommitted** trong working tree (`git status`), chưa commit theo đúng nguyên tắc "chỉ commit khi được yêu cầu".

---

## 1-2. Xác nhận không tin báo cáo cũ

```
git status        → working tree sạch tại thời điểm bắt đầu (527e26f)
git log -1         → 527e26f "feat(ui): specialist workspaces, manager dashboard v2, ..."
git diff HEAD~1..HEAD --stat → 373 files, phần lớn là graphify-out/ (tool phân tích code, không phải sản phẩm)
```

Danh sách module thật xử lý từng khái niệm (không suy luận từ tên nút UI):

| Khái niệm | Có backend thật? | Ghi chú |
|---|---|---|
| WorkItem (assignment cho Specialist) | **NOT IMPLEMENTED** ở runtime | Xem mục 3 |
| WorkItem (notification cho RM) | Có | `create_work_item()` / bảng `employee_work_items`, chỉ gọi từ `_notify_rm()` |
| Specialist review | Có, đầy đủ | `app/api/v2/employee_router.py:802-1006` (`submit_specialist_review`), bảng `specialist_reviews` |
| Customer document request | **NOT IMPLEMENTED** | Không có model/table/endpoint nào tên `DocumentRequest` trong toàn bộ `app/` (grep 0 kết quả) |
| Notification (RM) | Có | Tái dùng bảng `employee_work_items` |
| Notification (Specialist/Customer) | **NOT IMPLEMENTED** | Không có hàm `_notify_specialist`/`_notify_customer` nào |
| Timeline | Có, dạng derived | "Lịch sử tờ trình" trong `app.js` (`creditHistoryStepsHtml`) dựng từ cột timestamp có sẵn trong `corporate_credit_requests`, không phải bảng `TimelineEvent` riêng |
| Case state (SalesCase) | Có | `SharedCaseState` (Pydantic) → 1 dòng JSONB trong bảng `cases` |
| Next Best Work | Có, 2 tầng | `app/context/next_best_work.py` (dùng ở API thật) + `app/workflow/next_best.py` (dùng trong state machine nội bộ) — hai implementation riêng biệt, không phải trùng lặp lỗi, nhưng dễ nhầm |
| Approval (SalesCase) | Có | Bảng `approval_tokens`, RM-only (`owned()` gate trong `router.py`) |
| Approval (Credit Request) | Có | Cột `final_decision`/`approved_by` trong `corporate_credit_requests`, Manager-only |
| Role authorization | Có, đúng thiết kế | `require_verified_identity()` + `require_capability()`, nguồn thật = `SQLiteIAMAdapter`/`SQLiteSSOAdapter` đọc `data/mock_database/enterprise_core.sqlite3` |

---

## 3. Data model thật — chi tiết theo từng object

### SalesCase (`SharedCaseState`)
```
File: app/schemas/v2/shared_case_state.py:131-171
Database table: cases (SQLite: data/state/v2.sqlite3; Postgres nếu DATABASE_URL set)
Primary key: case_id
Foreign key tới case: (chính nó)
Status field: status (CaseStatus enum: new..completed/rejected/failed)
Created by: app/intake/service.py (IntakeService.create) hoặc app/api/v2/router.py POST /sales-cases
Assigned role: employee_id (chủ sở hữu RM), customer_id
API create: POST /api/v2/sales-cases (RM) hoặc customer intake facade
API read: GET /api/v2/sales-cases, GET /api/v2/cases/{id}
API update: nhiều endpoint trong router.py (confirm-profile, run-analysis, approve, execute-actions...) — tất cả gate bằng owned()
Frontend consumer: RM Workspace (app.js renderRuntime/loadCases)
```
**Toàn bộ 12 field nghiệp vụ** (`product_result`, `eligibility_result`, `credit_result`, `insurance_result`, `risk_gate_result`, `operations_result`, `next_best_questions`, `next_best_actions`, `ai_decision_log`, `audit_events`, `expert_findings`, `evidences`...) là `Dict[str, Any]`/`List[Dict[str, Any]]` **nhét chung trong 1 cột JSONB `state_json`** của bảng `cases` — đúng như prompt nghi ngờ. Không phải lỗi thiết kế (đây là event-sourced style, có version optimistic-locking), nhưng nghĩa là **không có cách nào query/index riêng một sub-object** (vd. "tất cả case đang chờ legal_specialist review") mà không load toàn bộ state.

### WorkItem
```
File: app/storage/employee_db.py:557-584 (get_work_items), 697-740 (create_work_item)
Database table: employee_work_items (data/state/v2.sqlite3 — SQLite, KHÔNG chung DB với cases nếu DATABASE_URL set cho Postgres, nhưng CÙNG file SQLite trong demo/local vì cả hai gọi settings.V2_DB_PATH khi DATABASE_URL rỗng)
Primary key: item_id
Foreign key tới case: KHÔNG có cột case_id — chỉ có customer_id; liên kết case_id (nếu có) nằm ẩn trong chuỗi item_id dạng "REVIEW-NOTIFY-{case_id}-{version}-..." và phải parse bằng regex phía frontend
Status field: status (pending/ready/completed) — không có ai transition nó sang "completed" khi RM thực sự xử lý xong (dead field ở runtime)
Created by: (a) seed tĩnh 1 lần trong init_employee_db() lúc server start; (b) _notify_rm() — CHỈ tạo item cho role_required="relationship_manager"
Assigned role: role_required
API create: KHÔNG CÓ endpoint HTTP nào để tạo WorkItem — chỉ tạo nội bộ (seed hoặc _notify_rm)
API read: GET /api/v2/me/work-queue (get_next_best_work)
API update: KHÔNG CÓ
Frontend consumer: RM/Specialist "Next Best Work" panel (app.js loadNextBestWorkQueue, loadSpecialistQueue) — CÙNG một endpoint cho cả hai
```
**Xác nhận bằng chạy thật:** `create_work_item()` toàn repo chỉ có **một** call site (`_notify_rm`, employee_router.py:727), luôn set `role_required=RoleType.RM.value`. Không có bất kỳ code path runtime nào tạo work item với `role_required="credit_specialist"/"legal_specialist"/"product_specialist"/"insurance_specialist"`. 4 dòng seed tĩnh (`TASK-201/301/401/501`, nội dung tiếng Việt cố định "Thẩm định điều kiện UBO chưa xác minh Minh Phát"...) là **toàn bộ** những gì 4 vai trò Specialist nhìn thấy trong "Specialist Work Queue", bất kể case thật nào được RM forward. Đã xác nhận bằng browser thật (mục 5).

### SpecialistReview
```
File: app/schemas/v2/specialist_review.py, app/storage/employee_db.py:615-694
Database table: specialist_reviews
Primary key: review_id
Foreign key tới case: case_id + case_version (pin theo đúng version bị block, chống stale-clear)
Status field: decision (cleared/blocked/needs_more_information)
Created by: POST /api/v2/cases/{case_id}/specialist-reviews (chỉ Specialist tự gọi cho chính mình, review_type PHẢI khớp role người gọi)
Assigned role: review_type (legal_specialist/product_specialist/credit_specialist)
API create: POST /api/v2/cases/{case_id}/specialist-reviews — app/api/v2/employee_router.py:802
API read: GET /api/v2/cases/{case_id}/specialist-reviews
API update: không có (append-only, đúng thiết kế)
Frontend consumer: RM Workspace "SPECIALIST APPROVALS" panel (specialistReviewsList)
```
Đây là endpoint **DUY NHẤT** thật sự đổi trạng thái case do một Specialist thao tác — đã verify hoạt động đúng qua gọi trực tiếp (debug, xem mục 13) và tạo work item RM + audit event thật.

### DocumentRequest
```
KHÔNG TỒN TẠI. grep "document_request|DocumentRequest" trên toàn bộ app/*.py → 0 kết quả (chỉ khớp các từ tiếng Việt không liên quan như "tài liệu"/"bổ sung" trong domain khác).
```
Không có model, không có table, không có endpoint. Khi Credit Specialist chọn "Yêu cầu RM bổ sung" hoặc Legal Specialist "needs_more_information", hệ thống KHÔNG tạo ra một đối tượng "yêu cầu tài liệu" độc lập nào — chỉ:
- Credit Request pipeline: set `status='WithRM'`, ghi `specialist_reason` (cột phẳng trong `corporate_credit_requests`, không SANH RA object riêng).
- SalesCase pipeline: append vào `next_best_questions` (JSON list trong state), tạo `NextBestQuestion` (không phải "document request", là "câu hỏi cần làm rõ" — khác ngữ nghĩa).

### Notification
```
KHÔNG có bảng/model Notification riêng.
RM: tái dùng bảng employee_work_items (_notify_rm) — hoạt động thật, đã verify.
Specialist: KHÔNG CÓ.
Customer: KHÔNG CÓ — Customer chỉ biết case đổi trạng thái bằng cách tự poll GET /api/v2/credit-requests và so `status` cũ/mới; không có bất kỳ push/badge/email nào.
```

### TimelineEvent
```
KHÔNG có bảng riêng. "Lịch sử tờ trình" (app.js:1367 creditHistoryStepsHtml) là hàm JS thuần dựng 4 bước cố định từ cột submitted_at/appraised_at/forwarded_at/decided_at có sẵn — đúng là derived view hợp lệ cho use case hẹp này, nhưng KHÔNG generalize được cho SalesCase pipeline hay bất kỳ event nào khác ngoài 4 mốc cứng đó.
```

### AuditEvent
```
File: app/storage/repository.py:500-545
Database table: audit_events
Primary key: sequence (BIGSERIAL) + event_id (unique)
Foreign key tới case: case_id, trace_id
Status field: (không có — append-only log)
Created by: repo.append_audit(...) — hash-chained (prev_hash/event_hash, SHA-256), verify_audit_chain() xác minh được toàn vẹn
API read: GET /api/v2/sales-cases/{id}/audit
Frontend consumer: RM Workspace tab "Audit"
```
Đây là phần làm TỐT và THẬT — hash-chain thực sự verify được, không phải placeholder. Xác nhận qua đọc mã, không phải phỏng đoán.

### NextBestWork
```
File: app/context/next_best_work.py (dùng bởi API thật) — 301 dòng, tính điểm ưu tiên từ business_impact/urgency/risk_severity/dependency_unblock/ownership_match/estimated_effort
Database table: employee_work_items (đọc), không ghi
API read: GET /api/v2/me/work-queue
```

### Approval
```
File: app/schemas/v2/shared_case_state.py:122-128 (SalesCase), app/storage/repository.py:547-565 (approval_tokens table)
SalesCase: Approval sub-model trong state, RM-only, gate bằng owned()
Credit Request: cột final_decision/approved_by trong corporate_credit_requests, Manager-only, gate bằng require_capability(identity, "credit:final_approve")
```
Hai cơ chế Approval **độc lập, không liên thông** cho hai pipeline khác nhau (xem mục 12).

---

## 4-5. RM → Specialist handoff và Specialist Queue

**Có HAI pipeline hoàn toàn khác nhau và không liên thông trong hệ thống**, cả hai đều được gọi là "case" trong UI, dễ gây nhầm lẫn khi audit:

1. **SalesCase pipeline** (RM Workspace, nút "Chuyển Chuyên viên kiểm tra" = `forwardToSpecialist()`)
2. **Credit Request pipeline** (form khách hàng riêng, nút "Bổ sung & chuyển chuyên viên thẩm định" = `forwardCreditRequest()`)

### 4a. SalesCase pipeline — nút "Chuyển Chuyên viên kiểm tra" (`forwardToSpecialist`, app.js:323-359)

**KẾT QUẢ CHẠY THẬT QUA BROWSER (Playwright, ảnh `reports/cross_role/07_rm_forward_specialist_button_salescase.png`):**
```
RM_TO_SPECIALIST (SalesCase button): BROKEN — xác nhận bằng browser thật
HTTP thật trả về: 422 POST /api/v2/cases/CASE-62D0E05BF2D8/specialist-reviews
Toast hiển thị cho RM: "✓ Đã ghi nhận chuyển Chuyên viên..." (THÀNH CÔNG GIẢ — catch-block generic che giấu lỗi thật, app.js:350-357)
```
**Nguyên nhân gốc (3 lớp lỗi xếp chồng, xác nhận bằng đọc mã + test trực tiếp từng lớp):**
1. `forwardToSpecialist()` gửi `findings:[note]` — `note` là 1 chuỗi string từ `prompt()`. Backend `SpecialistReviewRequest.findings: List[SpecialistReviewFinding]` yêu cầu object `{code, severity, message}`. Pydantic reject ngay ở tầng validate request body → **422 chính là lỗi này** (xác nhận: response thật khớp lỗi Pydantic, không phải lỗi nghiệp vụ).
2. Ngay cả khi (1) được sửa: endpoint `submit_specialist_review` check `if role != body.review_type: 403` — đây là endpoint để **Specialist tự nộp review của chính mình**, KHÔNG PHẢI endpoint "RM assign/forward". RM gọi với `review_type="legal_specialist"` trong khi role thật của RM là `relationship_manager` → luôn 403.
3. Ngay cả khi (2) được bỏ qua: `required_information:[]` (rỗng) trong khi `decision="needs_more_information"` → backend yêu cầu `required_information` không rỗng → 422 `REQUIRED_INFORMATION_REQUIRED`.

**Kết luận:** Nút "Chuyển Chuyên viên kiểm tra" trong RM Workspace hiện tại **không có cách nào thành công** — nó gọi nhầm endpoint (endpoint dành cho Specialist tự nộp kết quả, không phải để RM gán việc), và toast thành công là giả. Đây không phải lỗi 1 dòng — sửa đúng cần **thiết kế lại**: hoặc tạo endpoint "RM assign case to specialist" thật (tạo WorkItem với `role_required` đúng), hoặc bỏ nút này khỏi luồng RM và chỉ dựa vào risk-gate tự động đưa case vào `PENDING_REVIEW`. Không tự sửa trong lần audit này vì đây là quyết định thiết kế, không phải bug cơ học.

### 4b. Credit Request pipeline — nút "Bổ sung & chuyển chuyên viên thẩm định" (`forwardCreditRequest`)

**KẾT QUẢ CHẠY THẬT QUA BROWSER — THÀNH CÔNG** (sau khi sửa bug #1 ở mục 0):
```
WORK_ITEM_PERSISTED: N/A (pipeline này không dùng WorkItem — dùng cột status trên chính bảng corporate_credit_requests)
Case ID đúng: YES — case_id giữ nguyên xuyên suốt (CASE-AB192085C486)
Trạng thái trước: WithRM → sau: PendingAppraisal — XÁC NHẬN qua SQL trực tiếp sau khi bấm nút trên browser thật
assigned_rm_id: RM-999 — đúng
Audit event: có (specialist_reviews không áp dụng ở đây; audit riêng của credit-request qua JsonEventLogger `credit_request_forwarded`)
```
Ảnh: `reports/cross_role/06_rm_forward_to_credit_specialist.png`. Đây là pipeline THẬT SỰ hoạt động cho use case "RM forward hồ sơ cho Credit Specialist" mà prompt mô tả.

---

## 6. Specialist Queue

```
SPECIALIST_QUEUE (generic NBW queue, "/api/v2/me/work-queue"): HARD-CODED SEED DATA — xác nhận bằng browser thật
```
Đăng nhập `SPEC-CREDIT-001`, `SPEC-LEGAL-001`, `SPEC-PROD-001` qua browser thật: cả 3 chỉ thấy **đúng 1 item tĩnh** (`queue_item_count: 1`), nội dung y hệt seed trong `app/storage/employee_db.py` bất kể có case thật nào cần review hay không. Case thật đang chờ Legal review (`CASE-62D0E05BF2D8`, `required_reviewer_roles=["legal_specialist"]`, `status=pending_review`) — xác nhận tồn tại qua API — **không xuất hiện ở bất kỳ đâu** trên trang Specialist Workspace của SPEC-LEGAL-001 (`target_case_visible_anywhere_on_page: false`).

```
Frontend expected field: work_item_id dạng "REVIEW-NOTIFY-{case_id}-{version}-..." (để regex parse ra case_id, viewSpecialistTask app.js:1407-1424)
Backend returned field: work_item_id tĩnh dạng "TASK-201"/"TASK-301"/"TASK-401"/"TASK-501" cho tất cả case thật
Root cause: create_work_item() (nguồn duy nhất tạo work item runtime) chỉ tạo item cho role_required=relationship_manager (_notify_rm); không có code path nào tạo item cho 4 role Specialist khi risk-gate đưa case vào PENDING_REVIEW
Fix: cần thêm 1 hàm _notify_specialist(case, role) tương tự _notify_rm(), gọi tại thời điểm case chuyển sang PENDING_REVIEW (app/workflow/risk_gate.py hoặc engine.py), với role_required=required_reviewer_roles tương ứng — KHÔNG tự sửa trong lần audit này vì đụng vào workflow engine, cần xác nhận thiết kế trước.
```

Riêng **Credit Request pipeline có queue RIÊNG, THẬT SỰ hoạt động**: panel "TỜ TRÌNH TÍN DỤNG" trong Specialist Workspace (`loadCreditApprovalRequests`, gọi `GET /api/v2/credit-requests`) — đã verify hiển thị đúng request thật vừa được RM forward, đúng dữ liệu (company, số tiền, mục đích — kể cả marker unique tôi chèn để trace). Đây là 2 panel khác nhau trên CÙNG một trang Specialist Workspace — 1 panel thật (Credit Request), 1 panel giả (generic NBW Queue) — dễ gây hiểu nhầm "đã có queue" khi thực ra chỉ nửa đúng.

---

## 7. Needs More Information

**Chạy thật qua browser (Credit Specialist, click "Yêu cầu RM bổ sung"):**
```
SpecialistReview record created: N/A cho pipeline Credit Request (pipeline này không dùng bảng specialist_reviews — dùng cột phẳng); CÓ THẬT cho pipeline SalesCase (bảng specialist_reviews, verify qua debug-call mục 13)
WorkItem status updated: N/A (không áp dụng, xem mục 6)
Case status updated: YES — WithRM → xác nhận SQL trực tiếp
DocumentRequest created: NO — không tồn tại (mục 3)
RM notification created: CÓ, cho SalesCase pipeline (_notify_rm tạo work item thật, verify SQL); Credit Request pipeline: RM thấy qua đổi status khi tự load lại trang (không có push notification riêng)
Customer-visible request created: NO — customer chỉ thấy status field regress về "WithRM", giống hệt trạng thái vừa gửi lần đầu, KHÔNG có field nào phân biệt "cần bổ sung" (xác nhận qua field-diff, mục 8)
Timeline event created: CÓ, dạng derived (creditHistoryStepsHtml tự suy ra bước "② Chuyên viên thẩm định" chưa done)
Next Best Work recalculated: NO — không có trigger nào recalculate NBW khi credit request đổi trạng thái
```
→ **Đúng như prompt cảnh báo: "Nếu hệ thống chỉ ghi audit note nhưng không tạo DocumentRequest, chức năng chưa hoàn thành."** Xác nhận: hệ thống KHÔNG tạo DocumentRequest, chỉ đổi 1 cột status + 1 cột text nội bộ.

---

## 8. RM/Credit → Customer document request

**Chạy thật:** Logout Credit Specialist → login lại Customer (`USER-MP-001`) → mở "YÊU CẦU TÍN DỤNG".

```
Loại tài liệu cần bổ sung: KHÔNG HIỂN THỊ (không có field nào chứa thông tin này ở customer view)
Lý do: KHÔNG HIỂN THỊ
Trạng thái: "Chờ RM" / "WithRM" — Y HỆT trạng thái case vừa gửi lần đầu tiên, khách hàng KHÔNG THỂ phân biệt "đang chờ RM xử lý lần đầu" với "bị trả về vì thiếu hồ sơ"
Người yêu cầu: không có field
```
**Không có leak dữ liệu nội bộ** (đã verify field-by-field): `customer_visible_fields` không chứa `specialist_reason`, `specialist_recommendation`, `assigned_expert_id`, `appraisal_summary`, `agent_recommendation`, `rm_note` — đúng theo comment `_customer_view()` trong `credit_request_router.py:78-91` (whitelist tường minh). Đây là **thiết kế privacy có chủ đích, KHÔNG phải bug** — UI khách hàng có chú thích rõ: *"Bạn chỉ xem form và trạng thái công khai. Gợi ý Agent, nhận xét thẩm định và nội dung phê duyệt là dữ liệu nội bộ."* (app.js:929).

**Nhưng vì privacy boundary đó KHÔNG đi kèm với một cơ chế "public reason" nào thay thế** (không có DocumentRequest với 1-2 câu lý do công khai, an toàn), toàn bộ trải nghiệm "khách hàng nhận yêu cầu bổ sung tài liệu" mà prompt mô tả **hoàn toàn không tồn tại**. Ảnh: `reports/cross_role/12_customer_view_after_needs_more_info.png`.

---

## 9. Customer Resubmission

**Chạy thật:** Sau khi Credit Specialist yêu cầu bổ sung, logout Customer → login lại (phiên mới, giả lập đúng như prompt yêu cầu — không gọi API thủ công thay UI).

```
resume_possible: FALSE — xác nhận bằng browser thật
```
Nguyên nhân (đọc mã, xác nhận khớp hành vi quan sát được):
- `customerUi.caseId` (biến JS quyết định file upload/credit-request nối vào case nào) chỉ tồn tại **trong bộ nhớ trang hiện tại**, KHÔNG lưu `localStorage`/`sessionStorage`/cookie (grep `localStorage` trên toàn `app.js` → 0 kết quả).
- Danh sách "HỒ SƠ ĐÃ GỬI" (`#customerCaseList`) hiển thị bằng `<div>` tĩnh, KHÔNG có `onclick` — không có cách nào click để "mở lại" 1 case cũ.
- Kết quả thực tế: nếu customer logout/login lại (hoặc chỉ F5), thao tác "Tải hồ sơ và gửi RM kiểm tra" tiếp theo sẽ tạo **case_id MỚI HOÀN TOÀN**, đứt liên kết với case đang bị Specialist yêu cầu bổ sung.

→ **KHÔNG THỂ chạy hết chuỗi "Customer upload BCTC mới vào ĐÚNG case đang chờ"** qua giao diện như hiện có. Đây là gap thật, không phải giới hạn của bài test.

---

## 10-11. Selective Rerun / Next Best Work / Cleared Review

```
SELECTIVE_RERUN: đòn bẩy DUY NHẤT là RM bấm lại nút "Bổ sung & chuyển chuyên viên thẩm định" (forward lần 2) — xác nhận chạy thật qua browser: PendingAppraisal → (Credit Specialist needs_more_info) → WithRM → (RM re-forward) → PendingAppraisal → (Credit Specialist "Đề nghị trình phê duyệt") → PendingFinalApproval
```
Đây KHÔNG phải "chạy lại đúng phần Credit và giữ nguyên Product/Insurance" như prompt mô tả — pipeline Credit Request **không có khái niệm Product/Insurance output riêng để giữ nguyên** (nó không dùng chung state với SalesCase). "Rerun" ở đây thực chất là: risk-gate/status machine tự lùi 1 bước rồi RM đẩy tiến lại — không có signal "evidence mới đã sẵn sàng" khác với "RM tự tay bấm lại". Không có AgentRun version/timestamp riêng cho lần thẩm định thứ 2 (chỉ ghi đè `appraised_at`/`appraisal_summary` — **lần thẩm định trước bị mất, không giữ lịch sử**, xác nhận qua schema `corporate_credit_requests` — 1 cột `specialist_reason`/`appraisal_summary`, không phải bảng con nhiều dòng).

```
NEXT_BEST_WORK_UPDATE: KHÔNG xảy ra cho Credit Request pipeline (không có trigger); CÓ xảy ra cho SalesCase pipeline khi specialist review submit thành công (_notify_rm tạo work item mới, verify SQL)
```

**Cleared review (Credit Specialist "Đề nghị trình phê duyệt"):**
```
WorkItem = COMPLETED: N/A (không dùng WorkItem)
appraisal_status: "completed" — verify SQL
status: PendingFinalApproval — verify SQL
RM notification: có transition (RM có thể thấy qua reload danh sách), không có push riêng
Timeline: cập nhật (derived, đúng)
Audit: qua JsonEventLogger event "credit_request_appraised", không phải bảng audit_events hash-chain (khác với SalesCase pipeline)
```
**Về từ ngữ (mục 11 của prompt):** UI dùng đúng "Đề nghị trình phê duyệt" (recommend for approval) — KHÔNG dùng "Credit approved"/"Loan approved" ở bước Specialist. Từ "phê duyệt giải ngân" (approve disbursement) chỉ xuất hiện ở nút của Manager. **Đây là điểm làm đúng**, xác nhận qua đọc `creditStaffActionsHtml()` (app.js:897-921).

---

## 12. Proposal và Approval

Hai luồng approval hoàn toàn tách biệt:

| | SalesCase pipeline | Credit Request pipeline |
|---|---|---|
| Approval do ai | **Chỉ RM sở hữu case** (`owned()` gate, `app/api/v2/router.py`) | **Chỉ Manager** (`require_capability(identity,"credit:final_approve")`) |
| Endpoint | `POST /api/v2/sales-cases/{id}/approve` + `/execute-actions` (2 bước: preview hash → approve → execute, one-time token) | `POST /api/v2/credit-requests/{id}/decision` |
| Manager có quyền ở đây? | **KHÔNG** — không có endpoint approve nào cho Manager trong SalesCase pipeline | **CÓ, xác nhận chạy thật qua browser**: `final_status: "Approved"`, `final_decision: "approved"`, `approved_by: "MGR-HN-01"` |
| Payload/hash | `payload_hash` bắt buộc khớp đúng preview (SalesCase); Credit Request không có payload-hash lock, chỉ Idempotency-Key | |
| Manager Proposal Preview đầy đủ (product/credit/insurance/evidence/conditions/disclaimer) | Có tồn tại (`/approval-preview`) nhưng **chỉ RM xem được**, Manager không truy cập luồng này | Manager xem qua "renderCreditFormView" — hiển thị form khách hàng + Agent advisory + thẩm định chuyên viên, KHÔNG có "disclaimer"/"conditions" tường minh như prompt mô tả cho Proposal |

**Kết luận đúng theo yêu cầu của prompt:** vì Manager **CÓ** endpoint approval thật (đã verify chạy end-to-end qua browser + DB), không được viết "Manager chỉ có aggregate dashboard". Nhưng phạm vi approval của Manager **chỉ giới hạn ở Credit Request pipeline** — với SalesCase pipeline, Manager thực sự chỉ có aggregate dashboard. Cả hai câu đều đúng, tuỳ pipeline — cần nói rõ pipeline nào khi mô tả "Manager approval" để không đánh đồng.

---

## 13. Bốn Specialist role — xem bảng chi tiết trong `19_ROLE_IMPLEMENTATION_MATRIX.md`

Tóm tắt nhanh, đã verify chạy thật:
- **Credit Specialist**: hoạt động đầy đủ cho Credit Request pipeline (sau khi sửa 3 bug ở mục 0). Generic NBW queue vẫn là seed tĩnh.
- **Product Specialist** (`SPEC-PROD-001`): đăng nhập được, quyền tồn tại (`product:verify_fit`), NHƯNG không tìm thấy case thật nào trong hệ thống hiện có `required_reviewer_roles` chứa `product_specialist` để test end-to-end review thật; endpoint review submission dùng chung cơ chế đã verify hoạt động cho Legal (mục dưới) nên về mặt kỹ thuật hoạt động, nhưng **chưa quan sát được 1 lần chạy thật với case product-block**.
- **Legal Specialist**: **trigger thật tồn tại** — case `CASE-62D0E05BF2D8` có `required_reviewer_roles=["legal_specialist"]`, `reasons=["eligibility_hard_block"]` (rule `RULE-CASH-REVENUE-001`, doanh thu dưới ngưỡng cho `PROD-CASH-MGMT`). Gọi trực tiếp API (debug-only, đúng ngoại lệ prompt cho phép) với payload đúng schema → **201 Created**, case chuyển `pending_review → pending_information`, tạo work item RM thật (`REVIEW-NOTIFY-CASE-62D0E05BF2D8-...`) và audit event thật. **Backend hoạt động đúng.** Nhưng **qua UI thật, Legal Specialist không có cách nào tự tìm thấy case này** (mục 6) — nên toàn bộ trải nghiệm người dùng thật (không debug) là **NOT IMPLEMENTED / không thể chạy**.
- **Insurance Specialist**: **UI placeholder — NOT IMPLEMENTED, xác nhận bằng browser thật.** Dropdown đăng nhập ghi `INS-001`, nhưng persona thật trong DB là `SPEC-INSURANCE-001` (mismatch tuyệt đối, không có alias). Đăng nhập `INS-001` → `401 Sai tai khoan hoac mat khau` mọi lần. **Không có cách nào đăng nhập vai trò Insurance Specialist qua UI đang chạy.**

---

## 14. Manager

```
Aggregate dashboard: CÓ THẬT — GET /api/v2/me/team/workload query trực tiếp bảng cases/employee_work_items/employee_recommendation_feedback (không phải số giả), xác nhận qua đọc mã app/api/v2/employee_router.py:573-668 và browser thật (mgrTotalCases hiển thị đúng case_count 51 khớp health-check)
Approval authority: CÓ THẬT, nhưng CHỈ cho Credit Request pipeline (xem mục 12)
```
Không trộn hai khái niệm — đã tách rõ theo pipeline ở trên.

---

## Tổng kết production-readiness

| Hạng mục | Đã có? | Ghi chú |
| --- | --- | --- |
| Data strategy | Một phần | SalesCase là JSONB blob hợp lý cho event-sourcing, nhưng WorkItem/Notification/DocumentRequest thiếu model riêng |
| Retrieval quality | Không đánh giá trong scope này | Ngoài phạm vi cross-role check |
| Guardrails/HITL | Một phần | Specialist review có RBAC + human_review_allowed đúng; nhưng 2/3 bug approval do quyền demo-persona seed sai, không phải guardrail logic |
| Evaluation | Chưa | Không có test nào trong repo phủ được luồng cross-role thật (xem 18) trước khi audit này |
| Observability | Một phần | Audit hash-chain thật cho SalesCase; Credit Request chỉ có JsonEventLogger phẳng, không hash-chain |
| Reliability | Một phần | Idempotency-Key có ở Credit Request POST; forward/appraisal/decision đều idempotent thật (verify qua replay logic trong `credit_request_repository.py`) |
| Security/privacy | Có | Customer view whitelist rõ ràng, không leak dữ liệu nội bộ (verify field-diff thật) |

Xem `18_CROSS_ROLE_BROWSER_E2E.md` cho chi tiết test browser, `19_ROLE_IMPLEMENTATION_MATRIX.md` cho bảng 4 role, `20_EMPTY_FRONTEND_AUDIT.md` cho audit empty-state/dead-button.
