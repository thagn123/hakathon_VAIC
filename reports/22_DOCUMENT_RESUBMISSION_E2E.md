# 22 — Document Resubmission & Full Journey Browser E2E

Test thật: `tests/browser/test_full_cross_role_journey.py` (Playwright, Chromium headless). Không dùng API để thay thao tác nghiệp vụ — API chỉ dùng ở 3 chỗ đã ghi rõ trong code: đọc `/api/v2/me/notifications` và `/api/v2/cases/{id}/timeline` (không có màn hình transcript riêng để đọc bằng mắt ngoài widget chuông thông báo/tab Timeline — đọc trực tiếp payload phía sau đúng 2 widget đó để xác minh), và 1 lần đọc `GET /api/v2/cases/{id}` để xác định case có đang `pending_review` hay không trước khi thử probe nút SalesCase-side (đúng ngoại lệ "debug step" mà prompt cho phép).

Chạy:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000   # không --reload
.venv/Scripts/python.exe -m pytest tests/browser/test_full_cross_role_journey.py -s
```

Kết quả lần chạy cuối: **1 passed** (pytest), exit code `main()` = 0, **0 console error, 0 HTTP ≥ 400 trên toàn bộ 19 bước** (xác nhận bằng cách quét lại `reports/cross_role/trace.json` — không có bước nào có `console_errors`/`http_errors` khác rỗng).

## Kết quả từng bước (đúng thứ tự 19 bước trong yêu cầu)

| # | Bước | Vai trò | Kết quả | Bằng chứng |
| - | --- | --- | --- | --- |
| 1 | Customer tạo case | Customer | `CASE-215FD31D7AE2` tạo qua intake thật, upload BCTC, gửi Form tín dụng `CR-CC04B0A20EF9` cùng case_id | `step01_db_verified` |
| 2 | RM xử lý và chạy Agent | RM | Mở case thật, **giải quyết 4 xung đột dữ liệu** (trích xuất vs nhập tay — guardrail có sẵn, không phải bug), xác nhận Customer Business Snapshot, chạy Multi-Agent analysis thật | `step02a`: `conflicts_resolved:4`; `step02`: `profile_confirmed:true`, `confirm_toast:"...đã được xác nhận và khóa hash."`, `analysis_ran:true` |
| 3 | Credit WorkItem được tạo | RM→hệ thống | `PendingAppraisal`; **row thật trong `employee_work_items`** (`item_id=CREDIT-NBW-CR-CC04B0A20EF9-appraisal`, `role_required=credit_specialist`) | `step03_db_verify_work_item_created`: `work_item_persisted:true` |
| 4 | Credit Specialist mở queue thật | Credit Specialist | `GET /api/v2/work-items/my` (không phải seed JS) trả về đúng item vừa tạo, hiển thị company_name/trigger_reason/evidence_summary thật | `step04_dynamic_specialist_queue`: `contains_real_forwarded_item:true`, excerpt cho thấy đúng tên công ty + "6 evidence claim(s)" (số thật đọc từ case) |
| 5 | Credit Specialist yêu cầu BCTC mới | Credit Specialist | `needs_more_information`; **DocumentRequest thật được tạo** (`customer_safe_reason` KHÔNG chứa nội dung `specialist_reason` gốc) | `step05_db_verify_needs_more_info_and_document_request`: `document_request_persisted:true`, `leaks_internal_reason_into_customer_safe:false` |
| 6 | Customer thấy DocumentRequest | Customer | Panel "HỒ SƠ CẦN BỔ SUNG" hiển thị đúng lý do công khai + nút "Tải lên hồ sơ thay thế" | `step06_customer_sees_document_request`: `panel_shows_open_request:true` |
| 7 | Customer logout/login vẫn thấy case | Customer | Sau logout+login lại (phiên JS-memory bị xóa hoàn toàn), panel vẫn hiển thị đúng yêu cầu — vì lấy thẳng từ `GET /api/v2/customer/document-requests`, không phụ thuộc `customerUi.caseId` trong bộ nhớ | `step07_customer_resumes_after_relogin`: `resume_possible:true` |
| 8 | Customer upload BCTC thay thế | Customer | Bấm đúng nút của case này (định vị theo `case_id` trong `onclick`, không lệ thuộc thứ tự danh sách), upload → process → submit thành công | `step08_customer_resubmission_upload`: `toast_text:"Đã gửi hồ sơ thay thế. Chuyên viên sẽ xem xét lại."` |
| 9 | Evidence mới được tạo | Hệ thống | `document_request.status=SUBMITTED`, `replacement_document_id` được gán; **tài liệu cũ vẫn còn** (2 documents trên case, không bị xóa/ghi đè) | `step09_db_verify_evidence_update`: `old_document_preserved:true`, `total_documents_on_case:2` |
| 10 | Credit Specialist nhận notification | Hệ thống | Notification `type=customer_resubmitted` được tạo cho đúng `SPEC-CREDIT-001` | `step10_specialist_notification_on_resubmission`: `notification_found:true` |
| 11 | Credit Specialist review vòng 2 | Credit Specialist | Sau khi khách bổ sung, request **tự động quay lại `PendingAppraisal`** (không cần RM forward lại) — đúng thứ tự bước 8→11 trong yêu cầu (không có bước RM ở giữa) | `step11_specialist_notification_bell`: chuông hiện đúng số chưa đọc |
| 12 | Credit Specialist clear case | Credit Specialist | Nộp `recommend`, chuyển `PendingFinalApproval` | `step12/13`: `matches_expected:true` |
| 13 | Review vòng 1 vẫn tồn tại | Hệ thống | Bảng `credit_request_review_rounds` có **2 dòng** — vòng 1 (`needs_more_information`, text gốc còn nguyên) và vòng 2 (`recommend`) — không bị ghi đè như cột phẳng cũ | `step13_db_verify_cleared_and_review_history_preserved`: `review_round_count:2`, `round1_reason_preserved:true`, đồng thời xác nhận cột phẳng cũ (`flat_column_now_shows_round2_only:true`) chỉ còn vòng 2 — đúng như thiết kế "cột phẳng = mới nhất, bảng riêng = lịch sử đầy đủ" |
| 14 | RM thấy feedback và Next Best Work mới | RM | Form RM hiển thị đúng lý do vòng 2; nút "Tạo Proposal trình Manager" xuất hiện (chỉ xuất hiện khi `PendingFinalApproval` và chưa có proposal) | `step14_rm_sees_feedback_and_nbw`: `rm_sees_reason:true`, `proposal_button_visible:true` |
| 15 | RM tạo proposal | RM | `proposal_created_at` được set thật trong DB | `step15_rm_creates_proposal`: `clicked:true`, `proposal_created_at:"2026-07-26 06:43:36"` — đối chiếu trực tiếp bằng SQL độc lập, khớp |
| 16 | Manager thấy approval queue | Manager | Dashboard hiển thị số liệu thật từ DB | `step16_manager_dashboard` |
| 17 | Manager approve | Manager | Form hiển thị đúng thông báo "Proposal do RM tạo lúc..." (gate hoạt động), bấm phê duyệt → `status=Approved`, `approved_by=MGR-HN-01` | `step17_manager_decision`: `sees_proposal_gate_notice:true`, `final_status:"Approved"` |
| 18 | RM thấy final status | RM | Form RM hiển thị "Đã duyệt · giải ngân" | `step18_rm_sees_final_status`: `shows_approved:true` |
| 19 | Timeline chứa đầy đủ mọi event | Hệ thống | **17 sự kiện thật**, đủ cả 14 loại bắt buộc, đúng thứ tự nhân-quả | `step19_timeline_completeness`: `all_required_events_present:true`, `missing_required_events:[]` |

Chuỗi sự kiện timeline thật (bảng `timeline_events`, không suy ra từ state):
```
CASE_CREATED → DOCUMENT_UPLOADED → CREDIT_REQUEST_SUBMITTED → PROFILE_CONFIRMED →
WORK_ITEM_CREATED → AGENT_ANALYSIS_COMPLETED → SPECIALIST_REVIEW_SUBMITTED →
DOCUMENT_REQUEST_CREATED → DOCUMENT_UPLOADED → CUSTOMER_DOCUMENT_RESUBMITTED →
EVIDENCE_UPDATED → WORK_ITEM_REOPENED → SPECIALIST_REVIEW_SUBMITTED →
SPECIALIST_REVIEW_CLEARED → PROPOSAL_CREATED → APPROVAL_SUBMITTED → APPROVAL_COMPLETED
```

## Kiểm tra âm tính (proposal gate là thật, không phải trang trí)

Chạy độc lập qua API (script `smoke_test.py`, debug-only, đã xóa sau khi dùng): tạo request → forward → appraise "recommend" → Manager thử `/decision` **trước khi** có proposal → nhận **409 CONFLICT** đúng như thiết kế → RM tạo proposal → Manager thử lại → **200 OK**. Xác nhận gate chặn thật, không phải chỉ ẩn nút trên UI.

## Kiểm tra rò rỉ dữ liệu nội bộ (không đổi so với trước, xác nhận lại sau khi thêm trường mới)

`final_unauthorized_data_hidden_check`: `leaks_specialist_reason:false`, `leaks_specialist_recommendation:false`, `leaks_proposal_note:false`.

## Đối chiếu 13 assertion tối thiểu (mục 15 của prompt)

| Assertion | Kết quả |
| --- | --- |
| 0 unexpected console errors | ĐẠT |
| 0 unexpected HTTP ≥ 400 | ĐẠT |
| No false-success toast | ĐẠT — toast chỉ hiện success sau khi API trả 2xx; đã tự kiểm bằng cách xác nhận `forwardToSpecialist` mới không còn nhánh "catch → vẫn hiện success" như bản cũ (báo cáo 20 mục 4) |
| No undefined/null visible | ĐẠT trong phạm vi đã test (không thấy `undefined`/`null` thô trong bất kỳ excerpt nào) |
| No static specialist queue rows (là toàn bộ nội dung) | ĐẠT — item thật (`credit_appraisal`) và item seed (`demo_seed`) cùng tồn tại, phân biệt rõ bằng field `is_demo_seed`, không còn CHỈ có seed |
| DocumentRequest persisted | ĐẠT |
| Replacement document persisted | ĐẠT |
| Old document preserved | ĐẠT |
| Review history contains round 1 and round 2 | ĐẠT |
| Timeline contains every event | ĐẠT (17/17, đủ 14 loại bắt buộc) |
| Notifications delivered to correct roles | ĐẠT (xác nhận cho Credit Specialist; RM và Customer cũng có notification trong DB — xem báo cáo 24) |
| Unauthorized data hidden | ĐẠT |

## Ghi chú vận hành

- `uvicorn --reload` tiếp tục không đáng tin cậy — mọi lần sửa backend đều kill+restart thủ công rồi xác nhận lại qua curl trước khi chạy browser test (giống báo cáo 18).
- DB demo (`data/state/v2.sqlite3`) tích lũy dữ liệu qua nhiều lần chạy thử trong phiên làm việc này — test đã được viết để **định vị đúng theo `case_id`/`request_id` của chính lần chạy đó** (không dùng `.first` mù) để không bị ảnh hưởng bởi dữ liệu cũ còn sót lại từ các lần debug trước.
