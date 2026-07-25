# 01_IMPLEMENTATION_PLAN

## Mục tiêu hiểu được
Biến repository hiện tại thành một bản demo hoàn chỉnh, chạy trơn tru trên localhost, đủ tiêu chuẩn để quay video giới thiệu sản phẩm. Yêu cầu tập trung vào "Happy Path" với một kịch bản rõ ràng (Doanh nghiệp Minh Phát cần Payroll & Cash Management), có Fallback an toàn (không lỗi nếu API chết), UI chuẩn enterprise, và phải có tài liệu/scripts phục vụ việc chạy demo dễ dàng nhất.

## 1. Môi trường & Script Khởi động
- Tạo script `scripts/start_demo.ps1` và `start_demo.sh` giúp tự động setup `.env` an toàn, seed data và khởi động FastAPI uvicorn.
- Viết API `/api/v2/demo/seed` và `/api/v2/demo/reset` trong `router.py` để clear DB và insert mock data (Công ty Minh Phát) vào hệ thống (bảng `cases`, `intake_sessions`).

## 2. API Fallback & State minh bạch
- Bổ sung logic `DEMO FALLBACK` vào các Agent trong `app/agents/` hoặc giả lập response ở `api/v2/router.py` nếu `AGENTIC_LLM_ENABLED` tắt hoặc có lỗi từ API (try-except block).
- Response của Agent phải được chuẩn hoá theo JSON Schema có `status` (`EXPLORATORY`, `CONDITIONAL`, `EVIDENCE_SUPPORTED`, `NOT_SUPPORTED`, `NEED_REVIEW`), `evidence_refs`, `missing_information`.

## 3. Hoàn thiện UI Frontend (`app.js`, `index.html`, `app.css`)
- Thêm Header "DEMO MODE — SYNTHETIC DATA" và nút "Reset Demo".
- Thêm nút "Use Demo Data" ở màn hình Intake (Customer View) để auto-fill toàn bộ Form & Documents của "Công ty Minh Phát".
- Cập nhật giao diện `Agent Analysis` (Agent 1, Agent 2) để chia rõ cột/block: Product, Legal, Operations. Đánh màu trạng thái rõ ràng (Xanh/Vàng/Đỏ).
- Cải thiện màn hình "Missing documents" & "Next Best Work" (NBW). Đảm bảo không show JSON thô.
- Bổ sung trạng thái Loading chuyên nghiệp: "Building customer snapshot...", "Retrieving evidence...".

## 4. Dữ liệu Demo (Synthetic Data)
- Tạo thư mục `data/demo/` chứa `company_profile.json`, `product_catalog.json`.
- Chuẩn bị 3 file giả lập (Giấy đăng ký doanh nghiệp, Báo cáo tài chính, Danh sách nhân sự) để upload/fill.

## 5. Tài liệu & Kiểm thử
- Tạo `scripts/run_demo_smoke.py` thực hiện E2E call API kiểm tra toàn bộ luồng.
- Chạy thực tế bằng trình duyệt, chụp ảnh màn hình lưu vào `reports/screenshots/`.
- Cập nhật `README.md` và viết `DEMO_VIDEO_SCRIPT.md`.

## Open Questions
- Với phần AI Agents, hệ thống hiện đang dùng `Gemini` hay LLM provider nào? Việc fallback hoàn toàn offline (trả về JSON fix sẵn) được phép sử dụng ở mức độ nào?
- Việc giả lập tải file có thể chỉ là mock (bấm nút "Tải tài liệu mẫu") thay vì bắt buộc phải chọn file từ ổ cứng?

## Kế hoạch thực hiện chi tiết
1. Tạo Demo Data & Seed API.
2. Hoàn thiện Frontend: Nút "Use Demo Data", Nút "Reset", Loading State.
3. Hoàn thiện Backend Agent / Fallback.
4. UI: Trạng thái Evidence & NBW.
5. Kiểm thử & Chụp màn hình.
6. Viết Báo cáo & Tài liệu.
