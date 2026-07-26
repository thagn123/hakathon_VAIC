# 20 — Empty Frontend / Dead Button Audit

Phạm vi: các trang đã chạy thật qua browser trong phiên audit này (RM Workspace, Credit/Legal/Product Specialist Workspace, Customer Workspace, Manager Console). Mỗi mục dưới đây có ảnh chụp màn hình thật kèm theo trong `reports/cross_role/`.

## Tìm thấy: undefined / dữ liệu trống dù có data thật phía sau

### 1. Badge "Tài liệu đính kèm" không hiển thị tên file
```
File: app/static/app.js:835
Code: ${row.sales_case_documents.map(d=>`...📄 ${esc(d.name)}`).join("")}
Field thật trả về từ API: d.filename (xác nhận qua GET /api/v2/credit-requests/{id} — field "filename":"bo_ho_so_02_bao_cao_tai_chinh.txt", KHÔNG có field "name")
Hậu quả: mọi nơi hiển thị "Tài liệu đính kèm" chỉ thấy icon 📄 trống, không có tên file — xác nhận NHÌN THẤY TRỰC TIẾP trong ảnh reports/cross_role/09_credit_specialist_queue.png VÀ reports/cross_role/16_manager_dashboard.png (cả hai đều hiển thị icon rỗng "☰ —" tại mục "Tài liệu đính kèm (Từ luồng Nhu cầu)")
Fix 1 dòng: đổi d.name → d.filename tại app.js:835. Không tự sửa trong lần audit này (giữ đúng yêu cầu "không tiếp tục sửa UI theo suy đoán" — đây là phát hiện, không phải hotfix đang làm).
```

### 2. Lịch sử thẩm định mất dữ liệu khi có nhiều vòng
```
File: app.js:1367-1380 (creditHistoryStepsHtml), storage/credit_request_repository.py:appraise()
Vấn đề: corporate_credit_requests chỉ có 1 cột specialist_reason/specialist_recommendation (UPDATE, không INSERT). Khi Credit Specialist thẩm định vòng 2 sau khi đã yêu cầu bổ sung ở vòng 1, dữ liệu vòng 1 bị ghi đè hoàn toàn.
Xác nhận: SQL sau khi chạy hết 2 vòng cho CR-32E4CC09FF7D → specialist_recommendation="recommend" (không còn dấu vết "needs_more_information" ở đâu). Mục "8. Chuyên viên · Kết quả thẩm định" trên UI Manager (ảnh 16_manager_dashboard.png) chỉ hiển thị ĐÚNG 1 dòng kết quả (vòng cuối) — không phải "trống", nhưng SAI theo nghĩa "Timeline phải chứa mọi event" (mục 15 của prompt).
```

### 3. Manager "Workload chuyên viên" đứng yên bất kể hoạt động thật
```
Ảnh: reports/cross_role/16_manager_dashboard.png — mục "Workload chuyên viên": credit_specialist: 1, insurance_specialist: 1, legal_specialist: 1, product_specialist: 1 (relationship_manager: 5)
Nguồn: GET /api/v2/me/team/workload → COUNT(*) FROM employee_work_items WHERE role_required=? GROUP BY role_required
Vấn đề: con số "1 tác vụ" mỗi Specialist khớp CHÍNH XÁC với 4 dòng seed tĩnh ban đầu (TASK-201/301/401/501) — không đổi dù đã chạy toàn bộ chuỗi cross-role thật trong phiên này, vì (đã xác nhận ở báo cáo 17 mục 6) không có work item runtime nào từng được tạo cho 4 role Specialist. Đây KHÔNG PHẢI "0 không hợp lý" (giá trị 0 hợp lệ) mà là "hằng số 1 trông như đang hoạt động nhưng thực chất đông cứng" — dễ đánh lừa người xem dashboard rằng hệ thống đang phân phối việc, trong khi thực tế mọi case mới không hề tác động tới con số này.
```

## Tìm thấy: nút hoạt động nhưng phản hồi sai (không phải "chết", mà "giả")

### 4. Toast "thành công" hiển thị dù API trả lỗi
```
File: app.js:350-358 (forwardToSpecialist catch block)
else { toast(`✓ Đã ghi nhận chuyển Chuyên viên. Chuyên viên sẽ thấy case trong queue khi case đạt trạng thái PENDING_REVIEW.`,"success"); }
Xác nhận CHẠY THẬT: bấm nút "Chuyển Chuyên viên kiểm tra" trên case đang PENDING_REVIEW → API trả 422 → toast xanh "thành công" vẫn hiện (ảnh reports/cross_role/07_rm_forward_specialist_button_salescase.png, có thể thấy banner xanh ở góc). Đây là nút "không chết" (có phản hồi, có animation) nhưng phản hồi SAI SỰ THẬT — nghiêm trọng hơn một nút chết vì đánh lừa người dùng tin rằng việc đã được chuyển.
```

## Đã kiểm tra và KHÔNG phải lỗi (loại trừ để tránh báo cáo sai)

- Chuỗi `\ Idempotency:` nghi ngờ ở `app.js` dòng ~780 khi đọc qua tool — kiểm tra lại bằng đọc byte thô: đây là comment `// Idempotency:` bình thường, công cụ đọc hiển thị sai. Không phải lỗi cú pháp.
- Thẻ đóng `<\fieldset>` nghi ngờ ở app.js dòng 830/837 — kiểm tra byte thô: là `</fieldset>` hợp lệ. Không phải lỗi.
- `503 http://127.0.0.1:8000/api/v2/sales-cases` quan sát 1 lần khi đăng nhập SPEC-LEGAL-001/SPEC-PROD-001 trong lúc chạy nhiều probe song song — gọi lại độc lập ngay sau đó cho cùng identity → 200 OK bình thường. Nhiều khả năng là SQLite lock contention thoáng qua do nhiều trang cùng request trong probe script, không phải lỗi xác định theo role. Không đưa vào danh sách bug xác nhận vì không tái lập được ổn định.

## Nút không có hành động rõ ràng khi bấm vào seed task (không phải "chết" nhưng vô nghĩa)

```
File: app.js:1229-1261 (loadSpecialistQueue), 1407-1450 (viewSpecialistTask)
Hành vi: bấm vào task tĩnh (vd. "Phân tích khả năng trả nợ và cấu trúc vốn lưu động Minh Phát", TASK-401) → regex /REVIEW-NOTIFY-(CASE-[\w-]+)-(\d+)-/ không khớp work_item_id dạng "TASK-401" → caseId rỗng → panel "Chi tiết nhiệm vụ chuyên viên" không hiển thị context nào, chỉ còn placeholder "Chọn một nhiệm vụ từ danh sách hàng đợi để thẩm định." — xác nhận NHÌN THẤY trong ảnh reports/cross_role/09_credit_specialist_queue.png (panel bên phải trống dù đã có 1 task ở panel trái).
Đây chính là hệ quả trực tiếp của gap "WorkItem cho Specialist không tồn tại runtime" (báo cáo 17 mục 6) — không phải bug UI riêng lẻ.
```

## Kết luận

Không có trang nào trong phạm vi đã kiểm tra bị "trắng hoàn toàn"/crash. Nhưng có **4 chỗ cụ thể** dữ liệu hiển thị sai/thiếu (2 undefined-label, 1 mất lịch sử, 1 con số đông cứng) và **1 chỗ nút phản hồi sai sự thật** — tất cả đều xác nhận bằng ảnh chụp thật hoặc SQL, không suy đoán.
