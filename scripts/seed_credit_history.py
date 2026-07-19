"""Seed mock credit-history (lich su tin dung / CIC) rows for the Credit Agent.

Creates a ``credit_history`` table in enterprise_core.sqlite3 with one row per
credit facility (loan/guarantee) per customer, mimicking a CIC pull plus
internal repayment records. Scenarios are varied on purpose so the Credit
Agent has real signal to reason about:

- COMP-ABC  : sach, Nhom 1, tra dung han          -> agent nen "recommend"
- COMP-MP   : lich su ngan, 1 khoan da tat toan   -> agent nen "conditional"
- COMP-XYZ  : co cham tra 15 ngay trong 12 thang  -> Nhom 2, canh bao
- CUST-0008 : no xau da co cau lai                -> Nhom 3, hard block

Idempotent: rows are keyed by fixed record_id and INSERT OR REPLACE.
Run: python3 scripts/seed_credit_history.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/mock_database/enterprise_core.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS credit_history (
    record_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    source TEXT NOT NULL,                -- 'CIC' | 'SHB_INTERNAL'
    facility_type TEXT NOT NULL,         -- working_capital | term_loan | guarantee | trade_finance
    lender TEXT NOT NULL,
    cic_group INTEGER NOT NULL,          -- 1..5 theo phan loai no CIC
    original_amount_vnd REAL NOT NULL,
    outstanding_amount_vnd REAL NOT NULL,
    disbursed_at TEXT NOT NULL,
    maturity_at TEXT,
    status TEXT NOT NULL,                -- active | closed | overdue | restructured
    max_days_past_due_12m INTEGER NOT NULL,
    restructured INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    reported_at TEXT NOT NULL            -- ngay bao cao CIC gan nhat
)
"""

# (record_id, customer_id, source, facility_type, lender, cic_group,
#  original_vnd, outstanding_vnd, disbursed_at, maturity_at, status,
#  max_dpd_12m, restructured, note, reported_at)
ROWS = [
    # --- COMP-ABC: ho so sach, quan he tin dung dai, tra dung han ---
    ("CH-ABC-001", "COMP-ABC", "CIC", "working_capital", "SHB", 1,
     20_000_000_000, 12_500_000_000, "2023-03-10", "2026-03-10", "active",
     0, 0, "Han muc von luu dong quay vong, tra dung han 36 ky lien tiep.", "2026-06-30"),
    ("CH-ABC-002", "COMP-ABC", "CIC", "term_loan", "Vietcombank", 1,
     35_000_000_000, 8_000_000_000, "2021-08-01", "2026-08-01", "active",
     0, 0, "Vay trung han mua may moc, du no giam dan theo lich.", "2026-06-30"),
    ("CH-ABC-003", "COMP-ABC", "SHB_INTERNAL", "trade_finance", "SHB", 1,
     5_000_000_000, 0, "2024-01-15", "2024-07-15", "closed",
     0, 0, "LC nhap khau da tat toan dung han.", "2026-06-30"),

    # --- COMP-MP: lich su ngan (8 nam hoat dong nhung moi vay 1 lan) ---
    ("CH-MP-001", "COMP-MP", "CIC", "term_loan", "BIDV", 1,
     6_000_000_000, 0, "2022-05-20", "2025-05-20", "closed",
     4, 0, "Khoan vay duy nhat, da tat toan; co 1 ky cham 4 ngay (chua vao Nhom 2).", "2026-06-30"),

    # --- COMP-XYZ: dang co cham tra 15 ngay trong 12 thang gan nhat -> Nhom 2 ---
    ("CH-XYZ-001", "COMP-XYZ", "CIC", "working_capital", "Techcombank", 2,
     10_000_000_000, 7_200_000_000, "2024-02-01", "2026-02-01", "active",
     15, 0, "Cham tra goc 15 ngay ky 03/2026 do khach hang cham thu tien; da thanh toan du.", "2026-06-30"),
    ("CH-XYZ-002", "COMP-XYZ", "CIC", "guarantee", "SHB", 1,
     3_000_000_000, 3_000_000_000, "2025-09-01", "2026-09-01", "active",
     0, 0, "Bao lanh thuc hien hop dong van tai, chua phat sinh nghia vu.", "2026-06-30"),

    # --- CUST-0008 (Xay dung Dai Phat): no xau da co cau -> Nhom 3, hard block ---
    ("CH-0008-001", "CUST-0008", "CIC", "term_loan", "VPBank", 3,
     45_000_000_000, 31_000_000_000, "2022-11-01", "2027-11-01", "restructured",
     95, 1, "No qua han 95 ngay do cong trinh cham thanh toan; da co cau lai thoi han tra no.", "2026-06-30"),
    ("CH-0008-002", "CUST-0008", "CIC", "working_capital", "SHB", 2,
     8_000_000_000, 5_500_000_000, "2024-06-01", "2026-06-01", "overdue",
     35, 0, "Dang qua han 35 ngay ky gan nhat.", "2026-06-30"),
]


def seed() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(SCHEMA)
        cursor.executemany(
            """INSERT OR REPLACE INTO credit_history VALUES
               (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ROWS,
        )
        conn.commit()
        count = cursor.execute("SELECT COUNT(*) FROM credit_history").fetchone()[0]
        print(f"credit_history seeded: {count} rows in {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
