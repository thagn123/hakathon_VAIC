"""Full E2E demo flow test — exercises login, case creation, upload, profile confirm, analysis."""

from __future__ import annotations

import json
import os
import requests
import sys
import time

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://localhost:8000"


def _minimal_pdf(text: str = "Demo document content") -> bytes:
    """Generate a minimal valid PDF with the given text."""
    stream = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
    stream_bytes = stream.encode("latin-1")
    objects = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj",
        b"4 0 obj<</Length " + str(len(stream_bytes)).encode() + b">>stream\n" + stream_bytes + b"\nendstream endobj",
    ]
    body = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(body))
        body += obj + b"\n"
    xref_pos = len(body)
    xref = b"xref\n0 5\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    xref += b"trailer<</Size 5/Root 1 0 R>>\n"
    xref += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return body + xref


def _minimal_txt(text: str = "Demo text file content") -> bytes:
    return text.encode("utf-8")
RESULTS = []


def pretty(label: str, data, *, expect_ok: bool = True):
    status_icon = "✅" if expect_ok else "⚠️"
    print(f"\n{'='*60}")
    print(f"  {status_icon} {label}")
    print(f"{'='*60}")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:2000])
    else:
        print(str(data)[:2000])
    RESULTS.append({"step": label, "ok": expect_ok})


def safe_call(label: str, fn, *args, **kwargs):
    """Call fn, print result, return (response, data) or None on failure."""
    try:
        r = fn(*args, **kwargs)
        data = r.json() if "json" in (r.headers.get("content-type") or "") else r.text
        if r.ok:
            pretty(label, data, expect_ok=True)
            return r, data
        else:
            pretty(f"{label} (HTTP {r.status_code})", data, expect_ok=False)
            return r, data
    except Exception as exc:
        pretty(f"{label} (EXCEPTION)", {"error": str(exc)}, expect_ok=False)
        return None, None


def main():
    s = requests.Session()

    # 1. Health
    _, health = safe_call("1. Health Check", s.get, f"{BASE}/health")
    if health is None:
        print("Server is not running. Aborting.")
        sys.exit(1)

    # 2. Login as RM
    r, login = safe_call("2. Login as RM-999", s.post,
                         f"{BASE}/api/v2/auth/login",
                         json={"employee_id": "RM-999", "password": "demo1234"})
    if not r or not r.ok:
        print("Login failed. Aborting.")
        sys.exit(1)

    token = login.get("access_token", "")
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Employee-ID": "RM-999",
        "X-Session-ID": "SESS-MP",
    }
    json_headers = {**auth_headers, "Content-Type": "application/json"}

    # 3. Create Sales Case (Minh Phát)
    body = {
        "company_name": "Công ty Cổ phần Thiết bị Minh Phát",
        "tax_code": "0109988665",
        "industry": "Phân phối thiết bị công nghiệp",
        "contact": "Nguyễn Minh Anh · 0901 234 567",
        "employees_count": 500,
        "annual_revenue": 120000000000,
        "operating_years": 8,
        "requested_amount_vnd": 50000000000,
        "preferred_timeline": "Triển khai trong tháng này",
        "need_text": "Cần mở rộng kho bãi và hệ thống quản lý dòng tiền tự động cho 3 chi nhánh mới.",
        "rm_note": "Demo data — RM-999",
        "priority": "normal",
        "current_products": [],
    }
    r, case = safe_call("3. Create Sales Case", s.post,
                        f"{BASE}/api/v2/sales-cases",
                        json=body,
                        headers={**json_headers, "Idempotency-Key": f"e2e-{int(time.time())}"})
    if not r or not r.ok:
        print("Case creation failed. Aborting.")
        sys.exit(1)
    case_id = case["case_id"]
    version = case["version"]

    # 4. Upload mock documents
    files_payload = [
        ("files", ("Giay_DKKD_Minh_Phat.pdf", _minimal_pdf("Giay chung nhan DKKD - Cong ty Minh Phat - MST 0109988665"), "application/pdf")),
        ("files", ("BCTC_Minh_Phat_2025.pdf", _minimal_pdf("Bao cao tai chinh nam 2025 - Doanh thu 120 ty VND"), "application/pdf")),
        ("files", ("Danh_Sach_Nhan_Su.txt", _minimal_txt("Danh sach nhan su T5/2026 - Tong: 500 nguoi - 3 chi nhanh"), "text/plain")),
    ]
    r, upload = safe_call("4. Upload Documents", s.post,
                          f"{BASE}/api/v2/sales-cases/{case_id}/documents",
                          files=files_payload,
                          headers=auth_headers)
    if r and r.ok and isinstance(upload, dict):
        version = upload.get("version", version)

    # 5. Process documents
    r, process = safe_call("5. Process Documents", s.post,
                           f"{BASE}/api/v2/sales-cases/{case_id}/process-documents",
                           headers=json_headers)
    if r and r.ok and isinstance(process, dict):
        version = process.get("version", version)

    # 6. Get extracted profile
    safe_call("6. Extracted Profile", s.get,
              f"{BASE}/api/v2/sales-cases/{case_id}/profile",
              headers=json_headers)

    # 7. Confirm profile
    r, confirm = safe_call("7. Confirm Profile", s.post,
                           f"{BASE}/api/v2/sales-cases/{case_id}/confirm-profile",
                           json={"expected_version": version, "attestation": True},
                           headers=json_headers)
    if r and r.ok and isinstance(confirm, dict):
        version = confirm.get("version", version)

    # 8. Run analysis
    safe_call("8. Run Analysis", s.post,
              f"{BASE}/api/v2/sales-cases/{case_id}/run-analysis",
              json={"expected_version": version},
              headers=json_headers)

    # 9. List cases
    safe_call("9. List Sales Cases", s.get,
              f"{BASE}/api/v2/sales-cases",
              headers=json_headers)

    # Summary
    ok_count = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    print(f"\n{'='*60}")
    if ok_count == total:
        print(f"  ✅ ALL {total} STEPS PASSED")
    else:
        print(f"  ⚠️  {ok_count}/{total} STEPS PASSED")
        for r in RESULTS:
            if not r["ok"]:
                print(f"      FAILED: {r['step']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
