# 25 — Final Role & Demo Readiness

## 1. Đối chiếu Acceptance Criteria (mục 19 của prompt P0)

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| RM forward button | **PASS** | Endpoint mới `forward-to-specialist`, contract đúng yêu cầu, verify thật qua browser + API (báo cáo 22, 23) |
| WorkItem persistence | **PASS** | `employee_work_items` có row thật cho Credit Specialist (forward tờ trình) và Legal Specialist (forward-to-specialist) |
| Dynamic Specialist queue | **PASS** | `/work-items/my` đọc DB thật, phân biệt `is_demo_seed`, verify UI thật (báo cáo 22 `step04`) |
| Customer DocumentRequest | **PASS** | Bảng thật, endpoint thật, verify UI thật |
| Customer resume after login | **PASS** | Verify thật sau logout/login (báo cáo 22 `step07`) |
| Customer resubmission | **PASS** | Upload → process → submit, verify thật (báo cáo 22 `step08/09`) |
| Evidence update | **PASS** | Tài liệu mới + tài liệu cũ cùng tồn tại, verify SQL |
| Review version history | **PASS** | 2 round riêng biệt, round 1 không bị mất (báo cáo 22 `step13`) |
| Selective rerun | **Một phần** | Chỉ Credit Specialist re-thẩm định vòng 2 (đúng phạm vi bị ảnh hưởng); KHÔNG verify được việc "giữ nguyên output Product/Insurance" vì luồng test không có case nào có cả 3 domain cùng chạy — nhánh SalesCase (nơi có Product/Credit/Insurance cùng lúc) chưa có cơ chế "chỉ resume phần bị ảnh hưởng" tách biệt theo domain |
| Next Best Work update | **PASS** | `employee_work_items` cập nhật ở mọi mốc chính (forward, needs-info, cleared, reopened) |
| Real timeline events | **PASS** | 17/17 sự kiện, đủ 14 loại bắt buộc (báo cáo 24) |
| Notifications | **PASS** | Verify thật cho Customer/RM/Credit Specialist (báo cáo 24); Manager notification tạo đúng lúc RM proposal nhưng chưa tự tay verify bằng UI riêng cho Manager (chỉ verify bằng code path giống hệt các role khác) |
| Product Specialist path | **PARTIALLY INTEGRATED** | Cơ chế giống Legal 100%, chưa tự chạy 1 case thật (báo cáo 23) |
| Credit Specialist path | **PASS** | Đầy đủ, chạy hết 19 bước |
| Insurance Specialist path | **PARTIALLY INTEGRATED** | Login+RBAC đã sửa và verify; thiếu case kích hoạt thật trong dataset (gap dữ liệu, không phải gap code) |
| Legal Specialist path | **PASS** | Discovery path đã đóng hoàn toàn, verify thật (báo cáo 23) |
| Manager approval | **PASS** | Gate proposal hoạt động thật, verify cả 2 chiều (chặn khi chưa có proposal, cho qua khi đã có) |
| Cross-role browser E2E | **PASS** | `tests/browser/test_full_cross_role_journey.py`, 1 passed |
| Unexpected console errors | **0** | Xác nhận bằng quét toàn bộ `trace.json` |
| Unexpected HTTP errors | **0** | Như trên |
| False-success toast | **0** | `forwardToSpecialist` mới không còn nhánh che lỗi |

## 2. Kết luận theo đúng khung quyết định của prompt (mục 19)

> "Nếu Credit workflow hoàn thành nhưng các Specialist khác chưa có path: `FINAL STATUS: CREDIT WORKFLOW READY` / `OVERALL PRODUCT STATUS: PARTIALLY INTEGRATED`"

Đây đúng là tình huống hiện tại — nhưng **chính xác hơn cả điều kiện trên**, vì 2/4 Specialist role (Legal, và cơ chế dùng chung cho Product) đã có path thật, chỉ còn Insurance thiếu 1 lớp (dữ liệu kịch bản) và Product thiếu 1 lần chạy thử trực tiếp (không phải thiếu cơ chế).

```
CREDIT WORKFLOW STATUS: READY
OVERALL PRODUCT STATUS: PARTIALLY INTEGRATED
```

## 3. Rủi ro còn lại (nói thẳng, không giấu)

1. **Nhánh SalesCase Proposal Preview** (khác với nhánh Credit Request vừa hoàn thiện) — endpoint `/approval-preview` + `/approve` + `/execute-actions` cho case đa domain (Product+Credit+Insurance cùng lúc) tồn tại và đã có test cũ (`tests/test_sales_cases_e2e.py`) nhưng **không nằm trong phạm vi P0 lần này** (P0 tập trung vào Credit Request pipeline theo đúng chỉ định của prompt). Timeline mới **không** ghi `PROPOSAL_CREATED`/`APPROVAL_*` cho nhánh này.
2. **Insurance/Product Specialist**: cơ chế discovery+RBAC đã xong, nhưng để có 1 case thật kích hoạt `insurance_specialist` trong `required_reviewer_roles`, cần thêm rule mới vào `app/workflow/risk_gate.py` — đây là quyết định nghiệp vụ (rule gì kích hoạt bảo hiểm?), không tự ý thêm trong lần sửa bug này.
3. **`is_demo_seed` không tự dọn seed cũ** — theo đúng yêu cầu ("Seed demo được phép tạo... nhưng phải gắn demo=true"), 8 dòng `TASK-*` gốc vẫn còn trong `employee_work_items`, chỉ được đánh dấu khác biệt qua tiền tố `item_id`, không sửa schema bảng đó (giảm rủi ro cho một bảng đã được nhiều chỗ khác phụ thuộc — dashboard Manager, ranking NBW).
4. **Demo reset (`/api/v2/demo/reset`)** — đã xác nhận từ báo cáo 17 là nhắm sai file DB (`enterprise_core.sqlite3` thay vì `v2.sqlite3`), **chưa sửa trong lần P0 này** (không nằm trong 20 mục chỉ định rõ ràng; sửa nó đúng cách cần quyết định "reset đến mức nào" mà prompt mục 17 mô tả — vượt phạm vi thời gian của lần build này).
5. **`select_request_in_picker`/thứ tự dữ liệu demo tích lũy** — DB demo cục bộ (`data/state/v2.sqlite3`) đã tích lũy hàng chục case/request qua nhiều lần chạy thử trong phiên này; test đã được viết để miễn nhiễm với việc này (định vị theo ID chính xác), nhưng **một lần reset DB sạch trước khi demo thật cho ban giám khảo là khuyến nghị bắt buộc** để tránh gây nhiễu hình ảnh (ví dụ dashboard Manager hiện "Tổng Case: 56" — con số thật nhưng gồm toàn bộ rác từ quá trình phát triển).
6. **Role coverage test tự động** (mục 16 của prompt) — chưa đóng gói thành file test độc lập chạy lặp lại được; hiện tại verify bằng 1 script debug thủ công (đã chạy, kết quả ghi trong báo cáo 23, nhưng không nằm trong bộ test CI).

## 4. Khuyến nghị tiếp theo (không tự làm trong lần này)

- Trước khi demo thật: chạy một lần dọn dữ liệu (xóa `data/state/v2.sqlite3` và để hệ thống seed lại từ đầu, hoặc viết một script reset đúng file) để dashboard/queue không lẫn dữ liệu rác phát triển.
- Quyết định có đưa Insurance Specialist ra bản demo chính thức hay không — nếu có, cần bổ sung ít nhất 1 rule trong `risk_gate.py` để có case thật kích hoạt.
- Cân nhắc nối timeline/notification cho nhánh SalesCase Proposal Preview nếu ban giám khảo có khả năng đi theo nhánh đó thay vì Credit Request.
