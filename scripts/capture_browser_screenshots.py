"""Browser E2E test and screenshot generator using Playwright."""

from __future__ import annotations

import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCREENSHOT_DIR = "reports/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def run_browser_automation():
    console_errors = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("response", lambda res: failed_requests.append(f"{res.status} {res.url}") if res.status >= 400 else None)

        print("1. Opening Dashboard (http://localhost:8000)...")
        page.goto("http://localhost:8000", wait_until="networkidle")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_dashboard.png"))

        print("2. Clicking Reset Demo & Seed...")
        try:
            page.evaluate("fetch('/api/v2/demo/reset', {method: 'POST'})")
            time.sleep(1)
            page.reload(wait_until="networkidle")
        except Exception as e:
            print("Reset error:", e)

        print("3. Swapping to Customer Role and Auto-filling Demo Data...")
        try:
            # Select Customer role if role selector exists
            if page.locator("#role-select").is_visible():
                page.select_option("#role-select", "customer")
            time.sleep(0.5)
            
            # Click "Use Demo Data" button if visible
            demo_btn = page.locator("button:has-text('Use Demo Data'), button:has-text('Nạp dữ liệu mẫu')")
            if demo_btn.count() > 0 and demo_btn.first.is_visible():
                demo_btn.first.click()
                time.sleep(0.5)
        except Exception as e:
            print("Demo data fill note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_demo_data.png"))

        print("4. Switching to RM Role and opening Case Profile...")
        try:
            if page.locator("#role-select").is_visible():
                page.select_option("#role-select", "rm")
                time.sleep(0.5)
            # Click first case card or item if present
            case_item = page.locator(".case-item, .case-card, tr:has-text('Minh Phát')")
            if case_item.count() > 0 and case_item.first.is_visible():
                case_item.first.click()
                time.sleep(1)
        except Exception as e:
            print("Case select note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_profile.png"))

        print("5. Triggering Agent Analysis...")
        try:
            analyze_btn = page.locator("button:has-text('Chạy phân tích'), button:has-text('Run Analysis'), button:has-text('Phân tích Agent')")
            if analyze_btn.count() > 0 and analyze_btn.first.is_visible():
                analyze_btn.first.click()
                time.sleep(3)
        except Exception as e:
            print("Analyze click note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_agent_analysis.png"))

        print("6. Viewing Evidence Tab...")
        try:
            evidence_tab = page.locator("tab:has-text('Evidence'), button:has-text('Evidence'), .tab:has-text('Bằng chứng')")
            if evidence_tab.count() > 0 and evidence_tab.first.is_visible():
                evidence_tab.first.click()
                time.sleep(0.5)
        except Exception as e:
            print("Evidence tab note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_evidence.png"))

        print("7. Viewing Proposal Tab...")
        try:
            proposal_tab = page.locator("button:has-text('Tờ trình'), button:has-text('Proposal'), .tab:has-text('Đề xuất')")
            if proposal_tab.count() > 0 and proposal_tab.first.is_visible():
                proposal_tab.first.click()
                time.sleep(0.5)
        except Exception as e:
            print("Proposal tab note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_proposal.png"))

        print("8. Viewing Next Best Work / Action Panel...")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_next_best_work.png"))

        print("9. Viewing AI Trace / Log...")
        try:
            trace_btn = page.locator("button:has-text('Trace'), button:has-text('AI Log'), .tab:has-text('Trace')")
            if trace_btn.count() > 0 and trace_btn.first.is_visible():
                trace_btn.first.click()
                time.sleep(0.5)
        except Exception as e:
            print("Trace tab note:", e)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_ai_trace.png"))

        browser.close()

    print("\n--- BROWSER AUTOMATION COMPLETE ---")
    print(f"Screenshots saved to {SCREENSHOT_DIR}")
    print(f"Console errors detected: {len(console_errors)}")
    for err in console_errors:
        print("  -", err)
    print(f"Failed HTTP requests (>=400): {len(failed_requests)}")
    for freq in failed_requests:
        print("  -", freq)


if __name__ == "__main__":
    run_browser_automation()
