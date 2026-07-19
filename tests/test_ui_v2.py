"""Regression tests for the RM Workspace information hierarchy."""

from fastapi.testclient import TestClient

from app.main import app


def test_workspace_contains_login_and_verified_role_controls():
    html = TestClient(app).get("/").text
    for marker in ("loginScreen", "loginEmployee", "loginPassword", "roleBadge", "logoutButton"):
        assert marker in html


def test_workspace_exposes_a_clear_decision_reading_order():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text
    for label in (
        "Tóm tắt case",
        "Tiến trình xử lý",
        "Tạo yêu cầu phân tích",
        "Kết luận xử lý",
        "AI hiểu khách hàng cần gì?",
        "Sản phẩm nào phù hợp?",
        "Kết quả pháp lý theo sản phẩm",
        "Hành động ưu tiên",
        "Nguồn chứng minh kết luận",
        "Dữ liệu kỹ thuật JSON",
    ):
        assert label in html


def test_workspace_uses_real_input_and_explicit_rm_approval():
    html = TestClient(app).get("/").text
    for label in ("Nhập nhu cầu thật", "Chọn file tài liệu", "RM PHÊ DUYỆT BẮT BUỘC"):
        assert label in html
    assert "Case mẫu có hướng dẫn" not in html
    assert "Nạp bộ hồ sơ mẫu" not in html
