import sqlite3
import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone

def populate():
    db_path = Path("data/mock_database/enterprise_core.sqlite3")
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Load UBO verification status for mapping ubo_status
    ubo_status_map = {}
    ubo_file = Path("data/raw_csv_json/beneficial_owners.csv")
    if ubo_file.exists():
        with open(ubo_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cust_id = row["customer_id"]
                status = row["verification_status"]
                if cust_id not in ubo_status_map:
                    ubo_status_map[cust_id] = []
                ubo_status_map[cust_id].append(status)

    # 2. Load loan info for bad debt check
    bad_debt_set = set()
    loans_file = Path("data/raw_csv_json/loans.csv")
    if loans_file.exists():
        with open(loans_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cust_id = row["customer_id"]
                status = row["status"].lower()
                if status in ("defaulted", "bad_debt", "overdue"):
                    bad_debt_set.add(cust_id)

    # 3. Read and insert new customer profiles
    profiles_file = Path("data/raw_csv_json/enterprise_profiles.csv")
    if profiles_file.exists():
        with open(profiles_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cust_id = row["customer_id"]
                
                # Check UBO verification
                ubo_list = ubo_status_map.get(cust_id, [])
                if not ubo_list:
                    ubo_status = "Chưa xác minh đầy đủ"
                elif any(x in ("missing_verification", "unverified") for x in ubo_list):
                    ubo_status = "Chưa xác minh đầy đủ"
                else:
                    ubo_status = "Đầy đủ"
                
                # Bad debt check
                has_bad_debt = cust_id in bad_debt_set
                
                # Operating years from onboarding date
                try:
                    onboard_year = int(row["onboarding_date"].split("-")[0])
                    operating_years = max(1, 2026 - onboard_year)
                except Exception:
                    operating_years = 5
                
                # Build attributes matching the schema structure
                attributes = {
                    "name": row["company_name"],
                    "tax_code": row["tax_id_stub"],
                    "industry": row["industry_code"],
                    "employees_count": int(row["employee_count"]) if row["employee_count"].isdigit() else 100,
                    "annual_revenue": float(row["annual_revenue_vnd"]) if row["annual_revenue_vnd"].replace(".", "", 1).isdigit() else 50000000000.0,
                    "cash_flow_status": "Dòng tiền phân tán qua nhiều tài khoản phụ" if float(row.get("annual_revenue_vnd", 0)) > 100000000000 else "Tập trung tại một tài khoản chính",
                    "ubo_status": ubo_status,
                    "operating_years": operating_years,
                    "has_bad_debt_12m": has_bad_debt,
                    "account_or_unit_count": 4 if float(row.get("annual_revenue_vnd", 0)) > 100000000000 else 1,
                    "erp_system": "SAP Business One" if float(row.get("annual_revenue_vnd", 0)) > 150000000000 else "None"
                }
                
                # Insert or replace
                cursor.execute(
                    "INSERT OR REPLACE INTO customers(customer_id, profile_version, attributes) VALUES (?, ?, ?)",
                    (cust_id, "v1", json.dumps(attributes, ensure_ascii=False))
                )
                print(f"Inserted customer: {cust_id} - {row['company_name']}")

    # 4. Read and insert new employees and permissions
    raci_file = Path("data/raw_csv_json/raci_owner_directory.csv")
    if raci_file.exists():
        # Get list of all customer_ids currently in DB to assign as access scope for RMs
        all_customers = [r["customer_id"] for r in cursor.execute("SELECT customer_id FROM customers").fetchall()]
        
        with open(raci_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                employee_id = row["owner_id"]
                display_name = row["display_name"]
                team = row["team"]
                role_name = row["role"]
                
                # Determine system role mapping
                if "Specialist" in role_name or "Analyst" in role_name:
                    sys_role = "Specialist"
                elif "Lead" in role_name or "Manager" in role_name:
                    sys_role = "Manager"
                elif "RM" in role_name or "Relationship" in role_name:
                    sys_role = "RM"
                else:
                    sys_role = "Specialist"
                
                # Insert into employees
                cursor.execute(
                    "INSERT OR REPLACE INTO employees(employee_id, role, organization_unit) VALUES (?, ?, ?)",
                    (employee_id, sys_role, team)
                )
                
                # Build permissions and scope
                if sys_role in ("RM", "Manager"):
                    perms = ["case:read", "case:write", "approval:request", "credit:forward"]
                    scope = {
                        "managed_customer_ids": all_customers,
                        "branch": "HN01" if "Hanoi" in row.get("working_hours", "") else "HCM01"
                    }
                else:
                    perms = ["case:read"]
                    scope = {
                        "managed_customer_ids": [],
                        "branch": "HN01"
                    }
                
                # Insert into permissions
                cursor.execute(
                    "INSERT OR REPLACE INTO permissions(employee_id, permissions, access_scope) VALUES (?, ?, ?)",
                    (employee_id, json.dumps(perms), json.dumps(scope))
                )
                print(f"Inserted employee: {employee_id} ({display_name}) - role: {sys_role}")
                
    conn.commit()
    conn.close()
    print("Database populate completed successfully.")

if __name__ == "__main__":
    populate()
