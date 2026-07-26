# 23 — Specialist Role Coverage (cập nhật sau P0)

So với báo cáo 19 (trước P0), cơ chế **`POST /cases/{case_id}/forward-to-specialist`** (mục 2 của prompt P0) là điểm thay đổi cốt lõi: đây là cơ chế DUY NHẤT, DÙNG CHUNG cho cả 4 role, để RM giao một case thật cho một chuyên viên và tạo WorkItem thật — thay vì mỗi role có một con đường rời rạc, không đầy đủ như trước.

| Role | Có runtime Agent | Có WorkItem type | Có queue API thật | Có review API | Có case tạo được review | Feedback về RM | Kết luận (sau P0) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Credit Specialist | Có | Có (`CREDIT-NBW-*`, thật, tạo runtime) | Có — `/work-items/my` VÀ queue riêng của Credit Request pipeline | Có (`/appraisal` + `/specialist-reviews`) | **Có, chạy đầu-cuối qua browser 2 vòng** (báo cáo 22) | Có, verify thật | **IMPLEMENTED** — không đổi so với báo cáo 19, đã làm sâu hơn (versioning, resubmission, proposal) |
| Legal Specialist | Có (RAG thật) | Có (`FORWARD-*`, thật, tạo qua forward-to-specialist) | Có — `/work-items/my` | Có, đã verify chạy thật (debug call, báo cáo 19) | **Có — ĐÃ ĐÓNG GAP**: RM forward case `CASE-62D0E05BF2D8` (case có sẵn `required_reviewer_roles=[legal_specialist]`) qua UI/API forward-to-specialist → `201`, WorkItem thật → Legal Specialist đăng nhập, mở `/work-items/my`, thấy đúng task, bấm vào thấy **đúng ngữ cảnh thật** (`Mã hồ sơ: CASE-62D0E05BF2D8`, `eligibility_hard_block`, `RULE-CASH-REVENUE-001`) — không còn panel trống | Có (cơ chế đã verify ở báo cáo 19, không đổi) | **IMPLEMENTED** — gap "không có đường vào UI" (báo cáo 19) đã đóng hoàn toàn |
| Product Specialist | Có | Có (cơ chế forward-to-specialist dùng chung, chưa tự chạy live cho role này trong lần P0 này) | Có — `/work-items/my` (cùng cơ chế đã verify cho Legal) | Có (`/specialist-reviews`, không đổi) | **Chưa verify trực tiếp trong lần P0 này** — cơ chế giống hệt Legal (đã verify) nhưng chưa tự tay chạy 1 lần cho Product cụ thể | Có cơ chế (không đổi) | **PARTIALLY INTEGRATED** — hạ tầng giống Legal 100% (cùng 1 endpoint, chỉ khác `specialist_role` gửi lên), nhưng chưa tự thực hiện một lần chạy thật cho Product trong session này — khuyến nghị coi rủi ro thấp vì cơ chế đã chứng minh hoạt động cho Legal với cùng code path |
| Insurance Specialist | Có | Có (cơ chế forward-to-specialist dùng chung) | Có — `/work-items/my` | **Đã sửa RBAC**: `_REVIEWER_ROLES` nay gồm cả `insurance_specialist`; xác nhận bằng probe thật — gọi `/specialist-reviews` với `review_type=insurance_specialist` trả về `409 CASE_NOT_PENDING_REVIEW` (business-logic), **KHÔNG còn bị `422` schema rejection** như trước | Chưa có case thật nào trong dataset hiện có `insurance_specialist` trong `required_reviewer_roles` (không có rule nào trong `risk_gate.py` từng gán role này) — đây là **gap dữ liệu/kịch bản demo**, không phải gap code | Chưa verify (phụ thuộc gap trên) | **PARTIALLY INTEGRATED** — 3/4 lớp đã sửa xong và verify thật (login, RBAC, forward-to-specialist), lớp còn lại (case kích hoạt thật) cần một quyết định nghiệp vụ: thêm rule mới vào `risk_gate.py` để bao giờ đó gán `insurance_specialist` — nằm ngoài phạm vi sửa bug/tích hợp thuần túy |

## Bằng chứng cụ thể (không suy đoán)

**Insurance login qua UI thật** (trước đây `401` mọi lần):
```json
{"role_badge": "Role: Insurance Specialist", "login_error": "", "workspace_visible": true}
```

**RM forward case pháp lý cho Legal Specialist qua API forward-to-specialist**:
```json
{"status": 201, "body": {"work_item_id": "FORWARD-CASE-62D0E05BF2D8-legal_specialist-v2",
 "case_id": "CASE-62D0E05BF2D8", "assigned_role": "legal_specialist", "status": "OPEN", ...}}
```

**Legal Specialist mở task, thấy đúng ngữ cảnh thật (không còn panel trống)**:
```
Chi tiết nhiệm vụ Chuyên viên
Lý do chuyển: RM yeu cau legal_specialist kiem tra: Verify legal discovery path
Độ ưu tiên: high · Trạng thái: PENDING
Bối cảnh Hồ sơ & Quy tắc bị chặn
Mã hồ sơ: CASE-62D0E05BF2D8 (Phiên bản: 2)
eligibility_hard_block
Quy tắc kích hoạt: Rule ID: RULE-CASH-REVENUE-001
```
(`shows_placeholder_only: false` — so với báo cáo 20 mục "seed task click behavior" nơi panel luôn trống vì regex không khớp; nay dùng `case_id` trả về thẳng từ server, không còn phân tích chuỗi.)

**Insurance RBAC probe** (trước đây sẽ là `422` "review_type must be one of [...]"):
```json
{"status": 409, "body": {"detail": {"error": {"code": "CASE_NOT_PENDING_REVIEW", ...}}}}
```
409 nghĩa là request đã **vượt qua tầng schema/role validation** và chỉ dừng ở tầng business-logic không liên quan tới bảo hiểm (case không ở `pending_review`) — đúng là điều cần chứng minh: role không còn bị chặn ở tầng sai.

## Chưa làm trong lần P0 này (nói rõ, không giấu)

- Chưa tạo case thật nào có `insurance_specialist`/`product_specialist` trong `required_reviewer_roles` để chạy hết chuỗi review thật cho 2 role này (chỉ verify được cơ chế discovery + RBAC, chưa verify được bước "chuyên viên ra quyết định và case đổi trạng thái" cho chính 2 role này).
- Chưa build "role coverage test" tự động riêng (mục 16 của prompt) — việc verify ở trên được làm thủ công qua 1 script debug, chưa đóng gói thành test file lặp lại được trong CI.
- Dropdown đăng nhập vẫn hiển thị đủ cả 4 role dù Insurance/Product chưa full — theo đúng tinh thần "không ẩn role" đã thống nhất từ báo cáo 19, nhưng khuyến nghị cân nhắc thêm badge "hạn chế demo" nếu muốn minh bạch hơn với người dùng cuối.
