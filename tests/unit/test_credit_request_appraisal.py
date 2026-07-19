from app.credit.service import CreditReadinessService
from app.schemas.v2.credit_request import CorporateCreditRequestCreate


def request(**overrides):
    values = {
        "customer_id": "COMP-MP", "company_name": "Công ty Sao Mai", "tax_id": "0101234567",
        "legal_type": "Công ty cổ phần", "representative": "Nguyễn Văn A",
        "industry": "Sản xuất", "business_scale": "250 nhân sự",
        "total_assets_billion_vnd": 150, "net_revenue_billion_vnd": 500,
        "net_profit_billion_vnd": 25, "debt_to_equity_ratio": 1.8,
        "cic_debt_classification": "Nhóm 1 (Nợ đủ tiêu chuẩn)",
        "current_debt_billion_vnd": 40, "collateral_description": "Nhà máy",
        "collateral_value_billion_vnd": 60, "casa_avg_balance_billion_vnd": 5,
        "repayment_history": "Hoàn hảo", "request_type": "loan",
        "requested_amount_vnd": 5_000_000_000, "requested_term_months": 12,
        "purpose": "Bổ sung vốn lưu động nhập hàng.",
    }
    return CorporateCreditRequestCreate(**(values | overrides))


def test_agent_recommends_clean_request_without_approving_it():
    result = CreditReadinessService().appraise_request(request())

    assert result["recommendation"] == "recommend"
    assert result["score"] == 100
    assert "Credit Specialist" in result["summary"]


def test_agent_flags_high_risk_request_for_human_decision():
    result = CreditReadinessService().appraise_request(
        request(
            cic_debt_classification="Nhóm 3",
            debt_to_equity_ratio=4,
            net_profit_billion_vnd=-2,
            collateral_value_billion_vnd=1,
        )
    )

    assert result["recommendation"] == "not_recommended"
    assert result["score"] == 0


def test_agent_recommends_services_without_approving(monkeypatch):
    # Unit test the deterministic rule path; never hit the network.
    monkeypatch.setattr("app.config.settings.AGENTIC_LLM_ENABLED", False, raising=False)
    result = CreditReadinessService().recommend_services(request(industry="Xuất nhập khẩu"))

    names = {item["service"] for item in result["services"]}
    assert result["source"] == "rule"
    assert "Vốn lưu động / hạn mức tín dụng" in names
    assert "LC / Bảo lãnh thanh toán quốc tế" in names
    assert "Credit Specialist" in result["summary"]
