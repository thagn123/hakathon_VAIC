"""Seed mock corporate credit requests so the RM and final-approver queues have data.

Idempotent: rows are keyed by fixed request_id (CR-MOCK-*) and skipped if present.
Run: python3 tools/seed_mock_credit_requests.py
"""

from __future__ import annotations

from datetime import datetime

from app.storage import pg
from app.storage.pg import Json

COMPANIES = [
    ("COMP-ABC", "Công ty TNHH Thương mại ABC Việt Nam"),
    ("COMP-XYZ", "Công ty Cổ phần Sản xuất XYZ"),
]

BASE = dict(
    legal_type="Công ty TNHH",
    representative="Nguyễn Văn A",
    industry="C25 - Sản xuất sản phẩm từ kim loại",
    business_scale="120 nhân sự, 1 nhà máy",
    total_assets_billion_vnd=85,
    net_revenue_billion_vnd=140,
    net_profit_billion_vnd=9.5,
    debt_to_equity_ratio=1.4,
    cic_debt_classification="Nhóm 1 - Nợ đủ tiêu chuẩn",
    current_debt_billion_vnd=22,
    collateral_description="Nhà xưởng và quyền sử dụng đất KCN",
    collateral_value_billion_vnd=48,
    casa_avg_balance_billion_vnd=6.2,
    repayment_history="Đúng hạn 24 tháng gần nhất",
    request_type="loan",
    requested_term_months=36,
)

# (request_id, customer_id, company_name, tax_id, submitted_by, amount_vnd,
#  purpose, status, score, recommendation)
REQUESTS = [
    ("CR-MOCK-001", "COMP-ABC", "Công ty TNHH Thương mại ABC Việt Nam", "0101234567",
     "USER-ABC-001", 15_000_000_000, "Bổ sung vốn lưu động nhập hàng quý 4",
     "WithRM", 92, "recommend"),
    ("CR-MOCK-002", "COMP-XYZ", "Công ty Cổ phần Sản xuất XYZ", "0309876543",
     "USER-XYZ-001", 40_000_000_000, "Đầu tư dây chuyền sản xuất mới",
     "WithRM", 68, "conditional"),
    ("CR-MOCK-003", "COMP-MP", "Công ty TNHH Minh Phát", "0312345678",
     "USER-MP-001", 8_000_000_000, "Mở rộng kho bãi và mua thiết bị nâng hạ",
     "WithRM", 85, "recommend"),
    ("CR-MOCK-004", "COMP-ABC", "Công ty TNHH Thương mại ABC Việt Nam", "0101234567",
     "USER-ABC-001", 25_000_000_000, "Tài trợ hợp đồng xuất khẩu 12 tháng",
     "PendingApproval", 90, "recommend"),
    ("CR-MOCK-005", "COMP-XYZ", "Công ty Cổ phần Sản xuất XYZ", "0309876543",
     "USER-XYZ-001", 60_000_000_000, "Tái cấu trúc khoản vay trung hạn",
     "PendingApproval", 55, "not_recommended"),
]

SERVICES = [
    {"service": "Payroll", "priority": "high", "reason": "Trả lương 120 nhân sự qua SHB giúp tăng CASA."},
    {"service": "Internet Banking doanh nghiệp", "priority": "medium", "reason": "Quản lý dòng tiền giải ngân."},
]


def main() -> None:
    with pg.connect() as c:
        for tax_id, name in COMPANIES:
            c.execute(
                """INSERT INTO companies (tax_id, company_name, established_date, legal_form,
                       registered_address, business_address)
                   VALUES (?, ?, '2015-01-01', 'Công ty TNHH 2 thành viên trở lên', 'Hà Nội', 'Hà Nội')
                   ON CONFLICT (tax_id) DO NOTHING""",
                (tax_id, name),
            )

        created = 0
        for (rid, cust, name, tax, user, amount, purpose, status, score, rec) in REQUESTS:
            if c.execute("SELECT 1 FROM corporate_credit_requests WHERE request_id = ?", (rid,)).fetchone():
                continue
            summary = (
                f"Agent chấm điểm sơ bộ {score}/100 ({rec}). Dữ liệu mock phục vụ demo. "
                "Đây chỉ là khuyến nghị; quyết định cuối thuộc người phê duyệt."
            )
            pending = status == "PendingApproval"
            c.execute(
                """
                INSERT INTO corporate_credit_requests (
                    request_id, case_id, customer_id, submitted_by, company_name, tax_id,
                    legal_type, representative, industry, business_scale,
                    total_assets_billion_vnd, net_revenue_billion_vnd, net_profit_billion_vnd,
                    debt_to_equity_ratio, cic_debt_classification, current_debt_billion_vnd,
                    collateral_description, collateral_value_billion_vnd,
                    casa_avg_balance_billion_vnd, repayment_history, request_type,
                    requested_amount_vnd, requested_term_months, purpose,
                    status, appraisal_status, appraisal_summary, appraisal_score,
                    agent_recommendation, submission_idempotency_key,
                    assigned_rm_id, rm_note, service_recommendation,
                    service_recommendation_summary, forwarded_at, service_recommended_at,
                    submitted_at, appraised_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, 'completed', ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP - INTERVAL '1 day',
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    rid, f"CASE-{rid}", cust, user, name, tax,
                    BASE["legal_type"], BASE["representative"], BASE["industry"], BASE["business_scale"],
                    BASE["total_assets_billion_vnd"], BASE["net_revenue_billion_vnd"], BASE["net_profit_billion_vnd"],
                    BASE["debt_to_equity_ratio"], BASE["cic_debt_classification"], BASE["current_debt_billion_vnd"],
                    BASE["collateral_description"], BASE["collateral_value_billion_vnd"],
                    BASE["casa_avg_balance_billion_vnd"], BASE["repayment_history"], BASE["request_type"],
                    amount, BASE["requested_term_months"], purpose,
                    status, summary, score, rec, f"seed-{rid}",
                    "RM-999" if pending else None,
                    "RM đã kiểm tra hồ sơ, đề nghị phê duyệt." if pending else None,
                    Json(SERVICES) if pending else None,
                    "Đề xuất Payroll + Internet Banking để tăng CASA." if pending else None,
                    datetime.now() if pending else None,
                    datetime.now() if pending else None,
                ),
            )
            created += 1
        print(f"Seeded {created} mock credit request(s).")


if __name__ == "__main__":
    main()
