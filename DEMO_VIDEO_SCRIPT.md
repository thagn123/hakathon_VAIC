# SHB Corporate Expert Workspace — Demo Video Script

## Chuẩn bị
1. Mở terminal, cd vào thư mục dự án
2. Chạy `.\scripts\start_demo.ps1` (Windows) hoặc `./scripts/start_demo.sh` (Mac/Linux)
3. Mở trình duyệt tại `http://localhost:8000`

---

## Scene 1: Giới thiệu (30s)
**Hiển thị**: Trang chủ với banner đỏ "DEMO MODE — SYNTHETIC DATA & HUMAN IN THE LOOP"

> "Đây là SHB Corporate Expert Workspace — một hệ thống AI Copilot hỗ trợ RM ngân hàng doanh nghiệp trong quy trình tiếp nhận và phân tích nhu cầu khách hàng."

---

## Scene 2: Khách hàng gửi yêu cầu (45s)
1. Chọn **Role: Customer** → Đăng nhập
2. Bấm **"Use Demo Data"** → Form tự động điền thông tin Công ty Minh Phát
3. Bấm **"Gửi phiếu"** → Case được tạo
4. Upload 3 file hồ sơ → Documents chuyển cho RM

> "Khách hàng chỉ cần cung cấp thông tin một lần. Hệ thống gắn nguồn CUSTOMER_INPUT. RM sẽ tiếp nhận và đối chiếu."

---

## Scene 3: RM tiếp nhận & xử lý (60s)
1. Đăng xuất → Đăng nhập **Role: Staff → RM-999**
2. Chọn session **Minh Phát · COMP-MP**
3. Bấm vào Case mới tạo → Xem thông tin + documents
4. Bấm **"Tải lên hồ sơ"** nếu cần bổ sung, hoặc bấm **"Xử lý hồ sơ"**
5. Hệ thống phân loại tài liệu, trích xuất trường dữ liệu
6. Xem **Customer Business Snapshot** với confidence score
7. Bấm **"Xác nhận profile"** → Profile được RM confirm

> "RM đối chiếu dữ liệu từ CRM + tài liệu upload. Mỗi field có nguồn gốc rõ ràng: CRM, RM_INPUT, hay CUSTOMER_INPUT."

---

## Scene 4: AI Agent phân tích (60s)
1. Bấm **"Chạy phân tích Agent"**
2. Loading state hiện: "Đang phân tích..."
3. Kết quả hiện ra:
   - **Product Expert**: Gợi ý Payroll & Cash Management
   - **Credit Expert**: Phân tích khả năng tín dụng
   - **Insurance Expert**: Kiểm tra bảo hiểm tài sản/hàng hóa
   - **Coordinator**: Tổng hợp phương án cuối
4. Xem **Evidence Sources** tab → Nguồn trích dẫn từ catalog
5. Xem **AI Decision Log** → Trace rõ ràng

> "Mỗi Agent hoạt động độc lập. Coordinator tổng hợp nhưng không ghi đè hard rule. Mọi kết luận đều có evidence."

---

## Scene 5: Next Best Action & Phê duyệt (30s)
1. Panel phải hiện **Next Best Action**: "Gửi phê duyệt" hoặc "Bổ sung hồ sơ"
2. Nếu đủ điều kiện → Bấm **"Phê duyệt"**
3. Trạng thái chuyển thành `pending_approval` hoặc `completed`

> "Hệ thống chỉ ra đúng hành động tiếp theo. RM không cần đoán bước kế tiếp."

---

## Scene 6: Reset & Demo lại (10s)
1. Bấm nút **"↺ Reset Demo"** trên banner đỏ
2. Confirm → Dữ liệu xoá sạch, sẵn sàng demo lại

---

## Tổng kết (15s)
> "SHB Corporate Expert Workspace: Context-aware AI với Human-in-the-loop, giúp RM làm việc nhanh hơn, chính xác hơn, và luôn có evidence."

---

## Ghi chú kỹ thuật
- Dữ liệu hoàn toàn synthetic (DEMO MODE)
- Agent chạy deterministic fallback khi không có API key
- Tất cả chạy trên localhost, không cần kết nối cloud
- E2E test: 8/9 steps passed
