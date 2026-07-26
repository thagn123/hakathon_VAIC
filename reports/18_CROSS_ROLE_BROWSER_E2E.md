# 18 — Cross-Role Browser E2E

Test file thật: `tests/browser/test_full_cross_role_journey.py` (Playwright, Chromium headless, **không dùng API để thay thao tác UI** — mọi hành động nghiệp vụ là `page.click`/`page.fill`/`page.select_option` thật; API chỉ dùng để đọc dữ liệu customer-view và tìm case `pending_review` có sẵn, không dùng để thực hiện hành động nghiệp vụ thay UI).

Chạy:
```bash
.venv/Scripts/python.exe tests/browser/test_full_cross_role_journey.py
# hoặc
.venv/Scripts/python.exe -m pytest tests/browser/test_full_cross_role_journey.py -s
```
Yêu cầu server đang chạy tại `http://127.0.0.1:8000` (`uvicorn app.main:app --host 127.0.0.1 --port 8000`, không `--reload` — xem lý do ở mục "Ghi chú vận hành" bên dưới).

Output: `reports/cross_role/trace.json` (log máy đọc từng bước), `reports/cross_role/NN_*.png` (ảnh chụp toàn trang tại mỗi bước), `reports/cross_role/run_stdout.txt`.

**Đăng nhập lần lượt trong CÙNG một trình duyệt** (không phải nhiều context song song, nhưng đúng yêu cầu "đăng nhập lần lượt" của prompt): Customer → RM → RM (probe SalesCase) → Credit Specialist → RM → Customer → RM → Credit Specialist → Manager.

## Kết quả từng bước (run cuối cùng, sau khi sửa 3 bug ở báo cáo 17 mục 0)

| Bước | Vai trò | Hành động UI thật | Kết quả | Ảnh |
|---|---|---|---|---|
| 0 | Customer | Điền phiếu nhu cầu, gửi | Case `CASE-AB192085C486` tạo (SalesCase, "Hồ sơ nháp") | `02_customer_intake_submitted.png` |
| 0 | Customer | Upload `bo_ho_so_02_bao_cao_tai_chinh.txt` | Upload + process thành công | `03_customer_initial_upload.png` |
| 0 | Customer | Gửi Form yêu cầu tín dụng | `CR-32E4CC09FF7D` tạo, `case_id` = case ở trên, `status=WithRM` | `04_customer_credit_request_submitted.png` |
| 1 | RM | Chọn tờ trình, bấm "Bổ sung & chuyển chuyên viên thẩm định" | `status: WithRM → PendingAppraisal`, `assigned_rm_id=RM-999` (verify SQL) | `06_rm_forward_to_credit_specialist.png` |
| 1b | RM | Mở case `PENDING_REVIEW` có sẵn, bấm "Chuyển Chuyên viên kiểm tra" | **422** POST `.../specialist-reviews`; toast hiển thị "thành công" giả | `07_rm_forward_specialist_button_salescase.png` |
| 2 | Credit Specialist | Mở queue, chọn tờ trình, bấm "Yêu cầu RM bổ sung" | `status: PendingAppraisal → WithRM`, `specialist_recommendation=needs_more_information`, `specialist_reason` = đúng text đã nhập (verify SQL) | `10_credit_specialist_needs_more_info.png` |
| 3 | RM | Mở lại tờ trình | `rm_sees_reason: true` — RM đọc được đúng lý do Specialist vừa ghi | `11_rm_sees_specialist_feedback.png` |
| 4 | Customer | Mở "YÊU CẦU TÍN DỤNG" | Thấy `status="WithRM"` — KHÔNG phân biệt được với lần gửi đầu; không leak `specialist_reason`/`specialist_recommendation` | `12_customer_view_after_needs_more_info.png` |
| 5 | Customer | Logout → login lại, kiểm tra danh sách case cũ có bấm mở lại được không | `resume_possible: false` | `13_customer_case_list_after_relogin.png` |
| 6 | RM | Bấm forward lại | `status: WithRM → PendingAppraisal` | `14_rm_reforward_after_needs_more_info.png` |
| 7 | Credit Specialist | Bấm "Đề nghị trình phê duyệt" | `status: PendingAppraisal → PendingFinalApproval` (verify SQL) | `15_credit_specialist_cleared.png` |
| 8 | Manager | Dashboard | `mgrTotalCases` = số thật từ DB (khớp health-check) | `16_manager_dashboard.png` |
| 8 | Manager | Chọn tờ trình, điền lý do, bấm "Phê duyệt giải ngân" | `status: PendingFinalApproval → Approved`, `final_decision=approved`, `approved_by=MGR-HN-01` (verify SQL) | `17_manager_final_decision.png` |

Toàn bộ chuỗi 0→8 (trừ bước 1b, vốn là probe cố ý kiểm tra 1 nút riêng đã biết lỗi) **chạy thành công qua UI thật, có xác minh SQL độc lập sau mỗi bước.**

## Đối chiếu 13 assertion tối thiểu theo prompt (mục 15)

| Assertion | Kết quả | Ghi chú |
|---|---|---|
| No console error | **KHÔNG ĐẠT (có 1 chỗ, cố ý)** | Chỉ có ở bước 1b (probe nút biết lỗi). Toàn bộ luồng Credit Request chính (bước 0-8) không có console error nào. |
| No HTTP ≥ 400 | **KHÔNG ĐẠT (có 1 chỗ, cố ý)** | Cùng bước 1b: `422`. Luồng chính không có lỗi HTTP nào. |
| No undefined/null UI | **KHÔNG ĐẠT — 1 lỗi cụ thể tìm thấy** | Badge "Tài liệu đính kèm" trong form Credit Request hiển thị icon 📄 nhưng KHÔNG hiển thị tên file — `app.js:835` đọc `d.name` trong khi field thật trả về từ API là `d.filename`. Xem báo cáo 20. |
| WorkItem visible | **Một phần** | RM: có (verify SQL bảng `employee_work_items`). Specialist: không (mục 6, báo cáo 17). |
| Specialist review persisted | **Đạt** | `specialist_recommendation`/`specialist_reason` ghi đúng, verify SQL 2 lần (round 1 và round 2). |
| Customer request visible | **Đạt** | Customer thấy đúng request vừa gửi, đúng số liệu. |
| Resubmitted document visible | **Không thể kiểm chứng** | Không có cơ chế resubmit vào case cũ (mục 9, báo cáo 17) — không phải lỗi test, là gap thật của hệ thống. |
| Evidence updated | **Một phần** | Document gốc (upload lần đầu) liên kết đúng vào `sales_case_documents` của credit request (sau khi sửa bug #1) — verify qua API. Không test được "evidence sau resubmit" vì không resubmit được. |
| RM feedback visible | **Đạt** | `rm_sees_reason: true`, verify bằng đọc text thật trên trang RM. |
| Next Best Work changed | **Một phần** | Đổi cho RM (SalesCase pipeline, verify SQL work item mới). Không đổi cho Credit Request pipeline (không có trigger). |
| Timeline contains every event | **KHÔNG ĐẠT — phát hiện mất dữ liệu lịch sử** | Sau khi Credit Specialist thẩm định vòng 2 ("recommend"), cột `specialist_reason`/`specialist_recommendation` bị **ghi đè** — lý do "cần bổ sung BCTC" của vòng 1 **biến mất hoàn toàn**, không còn ở đâu trong DB. "Lịch sử tờ trình" trên UI chỉ dựng từ các cột phẳng nên cũng mất theo. Xác nhận bằng SQL: `specialist_reason` cuối cùng chỉ còn text vòng 2. |
| Unauthorized data hidden | **Đạt** | Field-diff xác nhận `specialist_reason`, `specialist_recommendation`, `rm_note`, `appraisal_summary`, `agent_recommendation` đều bị lọc khỏi customer view. |
| Final proposal rendered | **Không thực hiện trong phiên này** | Manager's credit-request form hiển thị dữ liệu form + Agent advisory (không phải "Proposal" đa domain product/credit/insurance/disclaimer đầy đủ như SalesCase `/approval-preview`). SalesCase Proposal Preview endpoint tồn tại và đúng RM-gated (đọc mã xác nhận), nhưng chưa chạy trực tiếp qua browser trong phiên audit này vì nút forward-to-specialist chặn đường tới `PENDING_APPROVAL` cho 1 case mới; case cũ đủ điều kiện thì đã ở trạng thái khác. Cần 1 phiên riêng để chạy hết SalesCase pipeline tới `execute-actions`. |

## Ghi chú vận hành quan trọng (ảnh hưởng cách chạy lại test này)

1. **`uvicorn --reload` không đáng tin cậy trong môi trường này.** Hai lần sửa file backend, `WatchFiles` không kích hoạt reload đúng lúc (xác nhận bằng log server không có dòng "WatchFiles detected changes" dù đã đợi >5s). Phải restart thủ công (kill + start lại không `--reload`) để đảm bảo code mới được nạp. Khuyến nghị: khi debug, luôn xác minh hành vi qua `curl` sau khi sửa code, đừng tin `--reload` đã áp dụng.
2. **`page.reload()` làm mất phiên đăng nhập** — ứng dụng không dùng `localStorage`/cookie, chỉ giữ token trong biến JS. Test ban đầu dùng `page.reload()` để lấy case list mới nhất, gây 403 giả (tưởng là bug quyền, thực ra là mất session do lỗi test). Đã sửa test dùng nút "↻ Tải lại" (`#refreshCases`) thay vì reload cứng.
3. **Một số action gọi LLM đồng bộ** (`create_credit_request` gọi Gemini cho service advisory; `appraise_credit_request` khi `recommendation≠needs_more_information` gọi lại appraiser) — có thể mất vài giây. Test dùng polling DB (`db_poll`/`get_request` với timeout tới 25s) thay vì `wait_for_timeout` cố định để tránh false-negative do timing.
