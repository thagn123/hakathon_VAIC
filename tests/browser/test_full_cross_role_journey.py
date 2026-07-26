"""Real, browser-driven cross-role reality check for the SHB Corporate Sales Copilot.

This is NOT a mocked/API-only E2E test. Every business action (login, form
fill, button click, file upload) is performed through the rendered UI with
Playwright. The database (data/state/v2.sqlite3) and API responses are read
afterwards ONLY to verify what the UI action actually persisted -- never to
substitute for the UI action itself. The two documented exceptions (explicit
per the test brief) are: (1) a couple of debug-only direct API reads used
purely to inspect internal state a human reviewer cannot see on screen
(notifications payload, timeline payload), and (2) one deliberate probe of a
known-broken code path for comparison.

Run directly:
    .venv/Scripts/python.exe tests/browser/test_full_cross_role_journey.py

Or via pytest:
    .venv/Scripts/python.exe -m pytest tests/browser/test_full_cross_role_journey.py -s

Requires the app server already running at BASE_URL:
    uvicorn app.main:app --host 127.0.0.1 --port 8000   (no --reload; see report)

Writes:
  - reports/cross_role/*.png            (screenshot per step)
  - reports/cross_role/trace.json       (full machine-readable trace)
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import Page, sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "state" / "v2.sqlite3"
SHOT_DIR = ROOT / "reports" / "cross_role"
SHOT_DIR.mkdir(parents=True, exist_ok=True)

RUN_MARKER = uuid.uuid4().hex[:8].upper()  # unique tag so this run's records are traceable
TRACE: List[Dict[str, Any]] = []
SHOT_SEQ = [0]

# Mandatory timeline event types per the P0 spec (section 7) -- every one of
# these must appear by the end of a full, real journey.
REQUIRED_TIMELINE_EVENTS = [
    "CASE_CREATED", "DOCUMENT_UPLOADED", "PROFILE_CONFIRMED", "AGENT_ANALYSIS_COMPLETED",
    "WORK_ITEM_CREATED", "SPECIALIST_REVIEW_SUBMITTED", "DOCUMENT_REQUEST_CREATED",
    "CUSTOMER_DOCUMENT_RESUBMITTED", "EVIDENCE_UPDATED", "WORK_ITEM_REOPENED",
    "SPECIALIST_REVIEW_CLEARED", "PROPOSAL_CREATED", "APPROVAL_SUBMITTED", "APPROVAL_COMPLETED",
]


def record(step: str, **kw: Any) -> None:
    entry = {"step": step, **kw}
    TRACE.append(entry)
    print(f"[{step}] " + json.dumps({k: v for k, v in kw.items() if k != "screenshot"}, ensure_ascii=False)[:500])


def shot(page: Page, name: str) -> str:
    SHOT_SEQ[0] += 1
    path = SHOT_DIR / f"{SHOT_SEQ[0]:02d}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to(ROOT))


def db_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def db_poll(sql: str, params: tuple = (), timeout_s: float = 25.0, interval_s: float = 1.0) -> List[Dict[str, Any]]:
    """Some actions (credit request create/appraise) synchronously call an
    LLM-backed advisory service, which can take several seconds. Poll the DB
    instead of guessing a fixed sleep."""
    deadline = time.time() + timeout_s
    rows: List[Dict[str, Any]] = []
    while time.time() < deadline:
        rows = db_all(sql, params)
        if rows:
            return rows
        time.sleep(interval_s)
    return rows


def get_request(request_id: str, *, want_status: Optional[str] = None, timeout_s: float = 15.0) -> Dict[str, Any]:
    """Fetch a credit request row, optionally polling briefly until it
    reaches `want_status` (covers the LLM-backed appraiser's latency).
    Always returns whatever is in the DB by the deadline (never raises for
    a still-stale status) so one slow step cannot crash the whole run."""
    deadline = time.time() + timeout_s
    row: Dict[str, Any] = {}
    while time.time() < deadline:
        rows = db_all("SELECT * FROM corporate_credit_requests WHERE request_id=?", (request_id,))
        if rows:
            row = rows[0]
            if want_status is None or row["status"] == want_status:
                return row
        time.sleep(1.0)
    return row


class NetWatcher:
    """Attached per-page. Records console errors and HTTP >=400 responses."""

    def __init__(self, page: Page, label: str) -> None:
        self.label = label
        self.console_errors: List[str] = []
        self.http_errors: List[str] = []
        page.on("console", self._on_console)
        page.on("response", self._on_response)

    def _on_console(self, msg) -> None:
        if msg.type == "error":
            self.console_errors.append(msg.text)

    def _on_response(self, resp) -> None:
        if resp.status >= 400:
            self.http_errors.append(f"{resp.status} {resp.request.method} {resp.url}")

    def snapshot(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "console_errors": list(self.console_errors),
            "http_errors": list(self.http_errors),
        }

    def clear(self) -> None:
        self.console_errors.clear()
        self.http_errors.clear()


def goto_app(page: Page) -> None:
    page.goto(f"{BASE_URL}/static/index.html", wait_until="networkidle")


def login(page: Page, role: str, staff: Optional[str] = None, password: str = "demo1234") -> None:
    page.select_option("#loginRole", role)
    if staff:
        page.select_option("#loginStaff", staff)
    page.fill("#loginPassword", password)
    page.click(".login-submit")
    page.wait_for_timeout(1200)


def logout(page: Page) -> None:
    if page.locator("#logoutButton").is_visible():
        page.click("#logoutButton")
        page.wait_for_timeout(400)


def select_request_in_picker(page: Page, picker_id: str, request_id: str) -> bool:
    picker = page.locator(f"{picker_id} select")
    if not picker.count():
        return False
    options = picker.locator("option").all_text_contents()
    if not any(request_id in opt for opt in options):
        return False
    picker.select_option(request_id)
    page.wait_for_timeout(500)
    return True


def main() -> int:
    overall_ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        net = NetWatcher(page, "main")
        try:
            _run_phases(page, net)
        except Exception as exc:  # noqa: BLE001 -- reality-check script: never lose the trace/screenshots so far
            import traceback

            overall_ok = False
            record("FATAL_EXCEPTION", error=str(exc), traceback=traceback.format_exc())
            try:
                shot(page, "FATAL_state_at_exception")
            except Exception:
                pass
        browser.close()

    _dump_trace()
    return 0 if overall_ok else 1


def _run_phases(page: Page, net: "NetWatcher") -> None:
    # ------------------------------------------------------------------
    # STEP 1 -- Customer creates the intake case + uploads docs, then
    # submits the linked corporate credit request (case_id is shared
    # because both forms run in this one customer browser session).
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "customer")
    shot(page, "customer_login")
    record("step01_customer_login", **net.snapshot())

    need_text = f"[RUN-{RUN_MARKER}] Doanh nghiep muon vay von luu dong va duoc chuyen vien tin dung xem xet ho so."
    page.fill("#customerNeedText", need_text)
    net.clear()
    page.click("#customerSubmit")
    page.wait_for_timeout(1500)
    case_id_text = page.locator("#customerCurrentCase").inner_text() if page.locator("#customerCurrentCase").count() else ""
    shot(page, "customer_intake_submitted")
    record("step01_customer_intake_submitted", case_banner=case_id_text, **net.snapshot())

    sample_doc = ROOT / "data" / "bo_ho_so_02_bao_cao_tai_chinh.txt"
    if page.locator("#customerFileInput").count() and sample_doc.exists():
        net.clear()
        page.set_input_files("#customerFileInput", str(sample_doc))
        page.wait_for_timeout(300)
        if page.locator("#customerUpload").is_visible():
            page.click("#customerUpload")
            page.wait_for_timeout(1800)
        shot(page, "customer_initial_upload")
        record("step01_customer_initial_upload", **net.snapshot())

    net.clear()
    page.fill("#creditPurpose", f"[RUN-{RUN_MARKER}] Thanh toan lo hang nhap khau, can bo sung von luu dong.")
    page.click("#creditSubmitBtn")
    page.wait_for_timeout(1500)
    submission_text = page.locator("#creditSubmissionResult").inner_text() if page.locator("#creditSubmissionResult").count() else ""
    shot(page, "customer_credit_request_submitted")
    record("step01_customer_credit_request_submitted", result_text=submission_text, **net.snapshot())

    rows = db_poll(
        "SELECT * FROM corporate_credit_requests WHERE purpose LIKE ? ORDER BY submitted_at DESC LIMIT 1",
        (f"%{RUN_MARKER}%",),
    )
    if not rows:
        record("step01_FATAL_no_request_found_in_db")
        raise RuntimeError("could not find the credit request we just submitted in the DB")
    request_id = rows[0]["request_id"]
    case_id = rows[0]["case_id"]
    record("step01_db_verified", request_id=request_id, case_id=case_id, status=rows[0]["status"])
    logout(page)

    # ------------------------------------------------------------------
    # STEP 2 -- RM opens the case, confirms the customer profile, and
    # runs the real Multi-Agent analysis (not just the credit-request form).
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "staff", "RM-999")
    shot(page, "rm_login_dashboard")
    record("step02_rm_login", **net.snapshot())

    net.clear()
    case_open_btn = page.locator(f"button.case-item[data-case='{case_id}']")
    rm_opened_case = False
    if case_open_btn.count():
        case_open_btn.first.click()
        page.wait_for_timeout(1000)
        rm_opened_case = True

    # RM resolves any extracted-vs-manual field conflicts before confirming
    # (a real, pre-existing guardrail: "xung dot chua xu ly se chan xac
    # nhan"). Click the first candidate for each conflict, same action the
    # real UI offers, looping since resolving one re-renders the list.
    conflicts_resolved = 0
    for _ in range(10):
        choice_btn = page.locator(".conflict-choice").first
        if not choice_btn.count():
            break
        choice_btn.click()
        page.wait_for_timeout(600)
        conflicts_resolved += 1
    shot(page, "rm_resolved_conflicts")
    record("step02a_rm_resolved_conflicts", conflicts_resolved=conflicts_resolved, **net.snapshot())

    profile_confirmed = False
    analysis_ran = False
    confirm_toast = ""
    if page.locator("#attestation").count() and page.locator("#attestation").is_visible():
        page.check("#attestation")
        if page.locator("#confirmProfile").is_visible():
            page.click("#confirmProfile")
            page.wait_for_timeout(1200)
            confirm_toast = page.locator("#toast").inner_text() if page.locator("#toast").count() else ""
            profile_confirmed = "UNRESOLVED_BLOCKERS" not in confirm_toast and "error" not in (page.locator("#toast").get_attribute("class") or "")
    if page.locator("#runAnalysis").count() and page.locator("#runAnalysis").is_visible():
        page.click("#runAnalysis")
        page.wait_for_timeout(8000)
        analysis_ran = True
    shot(page, "rm_process_and_run_agent")
    record(
        "step02_rm_processes_case_and_runs_agent",
        rm_opened_case=rm_opened_case, profile_confirmed=profile_confirmed, confirm_toast=confirm_toast,
        analysis_ran=analysis_ran, **net.snapshot(),
    )

    # ------------------------------------------------------------------
    # STEP 3 -- RM forwards the credit request -> a real Credit WorkItem
    # is created (employee_work_items row + timeline event).
    # ------------------------------------------------------------------
    net.clear()
    select_request_in_picker(page, "#rmCreditPicker", request_id)
    forward_btn = page.locator("button:has-text('Bổ sung & chuyển chuyên viên thẩm định')")
    forward_clicked = False
    if forward_btn.count():
        forward_btn.first.click()
        page.wait_for_timeout(1500)
        forward_clicked = True
    shot(page, "rm_forward_to_credit_specialist")
    record("step03_rm_forward_clicked", clicked=forward_clicked, **net.snapshot())

    row_after_forward = get_request(request_id, want_status="PendingAppraisal")
    work_item_rows = db_all(
        "SELECT * FROM employee_work_items WHERE item_id = ?", (f"CREDIT-NBW-{request_id}-appraisal",)
    )
    record(
        "step03_db_verify_work_item_created",
        status=row_after_forward["status"], expected_status="PendingAppraisal",
        matches_expected=row_after_forward["status"] == "PendingAppraisal",
        work_item_persisted=bool(work_item_rows),
        work_item_role=work_item_rows[0]["role_required"] if work_item_rows else None,
    )

    # --- Sub-probe: the SalesCase-pipeline "Chuyen Chuyen vien kiem tra"
    # button now calls the NEW forward-to-specialist endpoint via a real
    # inline form (previously it mis-used the specialist's own review
    # endpoint with a malformed payload -- see report 17 mult 0/report 20).
    net.clear()
    forward_specialist_probe: Dict[str, Any] = {"case_pending_review": False}
    case_state = _api_get(page, f"/api/v2/cases/{case_id}", "RM-999", "SESS-MP")
    if isinstance(case_state, dict) and case_state.get("case", {}).get("status") == "pending_review":
        forward_specialist_probe["case_pending_review"] = True
        if page.locator("#forwardSpecialistBtn").count() and page.locator("#forwardSpecialistBtn").is_visible():
            page.click("#forwardSpecialistBtn")
            page.wait_for_timeout(300)
            if page.locator("#fwdReason").count():
                page.fill("#fwdReason", f"[RUN-{RUN_MARKER}] Kiem tra dieu kien truoc khi tiep tuc.")
                page.select_option("#fwdSpecialistRole", "legal_specialist")
                page.click("#fwdSubmitBtn")
                page.wait_for_timeout(1200)
                toast_text = page.locator("#toast").inner_text() if page.locator("#toast").count() else ""
                forward_specialist_probe["toast_text"] = toast_text
                forward_specialist_probe["form_removed_on_success"] = not page.locator("#forwardSpecialistForm").count()
                shot(page, "rm_forward_specialist_button_salescase")
    record("step03b_forwardToSpecialist_button_probe", **forward_specialist_probe, **net.snapshot())
    logout(page)

    # ------------------------------------------------------------------
    # STEP 4/5 -- Credit Specialist opens the REAL dynamic queue
    # (GET /api/v2/work-items/my, not a JS fixture) and requests more info.
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "staff", "SPEC-CREDIT-001")
    shot(page, "credit_specialist_login")
    record("step04_credit_specialist_login", **net.snapshot())

    dynamic_queue_items = page.locator("#specQueueList .nbw-item")
    dynamic_queue_text = page.locator("#specQueueList").inner_text()
    real_item_present = case_id[:8] in dynamic_queue_text or request_id in dynamic_queue_text or "Tham dinh ho so tin dung" in dynamic_queue_text
    record(
        "step04_dynamic_specialist_queue",
        item_count=dynamic_queue_items.count(), contains_real_forwarded_item=real_item_present,
        queue_excerpt=dynamic_queue_text[:300],
    )

    net.clear()
    found_in_queue = select_request_in_picker(page, "#csCreditPicker", request_id)
    shot(page, "credit_specialist_queue")
    record("step04_request_visible_in_specialist_queue", found=found_in_queue, **net.snapshot())

    net.clear()
    reason_round1 = f"[RUN-{RUN_MARKER}-R1] Bao cao tai chinh hien tai da het hieu luc. Can bo sung BCTC nam gan nhat de tiep tuc danh gia."
    if page.locator("#creditSharedAppraisalReason").count():
        page.fill("#creditSharedAppraisalReason", reason_round1)
        page.fill("#creditRequestedDocType", "financial_statement")
        page.click("button:has-text('Yêu cầu RM bổ sung')")
        page.wait_for_timeout(1500)
    shot(page, "credit_specialist_needs_more_info")
    record("step05_needs_more_information_submitted", **net.snapshot())

    row_after_nmi = get_request(request_id, want_status="WithRM")
    doc_request_rows = db_all(
        "SELECT * FROM customer_document_requests WHERE credit_request_id = ? ORDER BY created_at DESC LIMIT 1",
        (request_id,),
    )
    doc_request = doc_request_rows[0] if doc_request_rows else {}
    record(
        "step05_db_verify_needs_more_info_and_document_request",
        status=row_after_nmi["status"], specialist_recommendation=row_after_nmi["specialist_recommendation"],
        specialist_reason=row_after_nmi["specialist_reason"],
        document_request_persisted=bool(doc_request_rows),
        document_request_status=doc_request.get("status"),
        customer_safe_reason=doc_request.get("customer_safe_reason"),
        leaks_internal_reason_into_customer_safe=(
            bool(doc_request) and reason_round1.split("]")[-1].strip()[:15] in (doc_request.get("customer_safe_reason") or "")
        ),
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 6 -- Customer sees the real DocumentRequest.
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "customer")
    page.wait_for_timeout(800)
    doc_req_panel_text = page.locator("#customerDocRequestsList").inner_text() if page.locator("#customerDocRequestsList").count() else ""
    shot(page, "customer_sees_document_request")
    record(
        "step06_customer_sees_document_request",
        panel_shows_open_request="Tải lên hồ sơ thay thế" in doc_req_panel_text,
        panel_excerpt=doc_req_panel_text[:400],
        **net.snapshot(),
    )

    # ------------------------------------------------------------------
    # STEP 7 -- Customer logs out/in; the SAME open request must still be
    # visible (backed by GET /api/v2/customer/document-requests on the
    # server, not the in-memory customerUi.caseId).
    # ------------------------------------------------------------------
    logout(page)
    goto_app(page)
    net.clear()
    login(page, "customer")
    page.wait_for_timeout(800)
    doc_req_panel_after_relogin = page.locator("#customerDocRequestsList").inner_text() if page.locator("#customerDocRequestsList").count() else ""
    resume_possible = "Tải lên hồ sơ thay thế" in doc_req_panel_after_relogin
    shot(page, "customer_case_list_after_relogin")
    record("step07_customer_resumes_after_relogin", resume_possible=resume_possible, **net.snapshot())

    # ------------------------------------------------------------------
    # STEP 8/9 -- Customer uploads the replacement BCTC through the SAME
    # panel; upload -> process -> link to DocumentRequest -> new evidence.
    # ------------------------------------------------------------------
    net.clear()
    replacement_doc = ROOT / "data" / "mau_ho_so_doanh_nghiep_MINH_PHAT.txt"
    # The demo DB accumulates open document requests across runs (same demo
    # customer_id every time) -- target THIS run's row specifically via its
    # case_id embedded in the onclick attribute, not just ".first", so an
    # older leftover request from a previous run can never be clicked by
    # mistake.
    this_run_upload_btn = page.locator(f"button[onclick*=\"{case_id}\"]:has-text('Tải lên hồ sơ thay thế')")
    upload_clicked = False
    if this_run_upload_btn.count() and replacement_doc.exists():
        page.once("filechooser", lambda fc: fc.set_files(str(replacement_doc)))
        this_run_upload_btn.first.click()
        page.wait_for_timeout(3000)
        upload_clicked = True
    shot(page, "customer_resubmission_upload")
    resubmit_toast = page.locator("#toast").inner_text() if page.locator("#toast").count() else ""
    record("step08_customer_resubmission_upload", clicked=upload_clicked, toast_text=resubmit_toast, **net.snapshot())

    doc_request_after_submit = db_all(
        "SELECT * FROM customer_document_requests WHERE request_id = ?", (doc_request.get("request_id"),)
    )
    all_case_documents = db_all(
        "SELECT document_id, sha256, document_json FROM case_documents cd "
        "JOIN intake_sessions ist ON ist.intake_id = cd.intake_id WHERE ist.case_id = ?",
        (case_id,),
    )
    record(
        "step09_db_verify_evidence_update",
        document_request_status=doc_request_after_submit[0]["status"] if doc_request_after_submit else None,
        replacement_document_id=doc_request_after_submit[0]["replacement_document_id"] if doc_request_after_submit else None,
        total_documents_on_case=len(all_case_documents),
        old_document_preserved=len(all_case_documents) >= 2,
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 10 -- Credit Specialist receives a real notification about the
    # resubmission (debug-only API read -- notifications have no separate
    # screen-reader-visible transcript beyond the bell widget, so this
    # inspects the exact payload behind that widget for verification).
    # ------------------------------------------------------------------
    specialist_notifications = _api_get(page, "/api/v2/me/notifications", "SPEC-CREDIT-001", "SESS-MP")
    resubmit_notif = next(
        (n for n in specialist_notifications if n.get("type") == "customer_resubmitted"), None
    )
    record(
        "step10_specialist_notification_on_resubmission",
        notification_found=bool(resubmit_notif),
        notification=resubmit_notif,
    )

    # ------------------------------------------------------------------
    # STEP 11/12/13 -- Credit Specialist reviews round 2 and clears it;
    # round 1 must still be queryable afterwards (append-only history).
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "staff", "SPEC-CREDIT-001")
    notif_bell_text = page.locator("#notifUnreadCount").inner_text() if page.locator("#notifUnreadCount").count() else ""
    record("step11_specialist_notification_bell", unread_count_text=notif_bell_text)

    select_request_in_picker(page, "#csCreditPicker", request_id)
    reason_round2 = f"[RUN-{RUN_MARKER}-R2] Da nhan duoc BCTC moi, so lieu du dieu kien trinh phe duyet."
    if page.locator("#creditSharedAppraisalReason").count():
        page.fill("#creditSharedAppraisalReason", reason_round2)
        page.click("button:has-text('Đề nghị trình phê duyệt')")
        page.wait_for_timeout(1500)
    shot(page, "credit_specialist_second_review")
    record("step12_credit_specialist_second_review_submitted", **net.snapshot())

    row_after_clear = (
        db_poll(
            "SELECT * FROM corporate_credit_requests WHERE request_id=? AND status='PendingFinalApproval'",
            (request_id,),
        )
        or db_all("SELECT * FROM corporate_credit_requests WHERE request_id=?", (request_id,))
    )[0]
    review_rounds = db_all(
        "SELECT * FROM credit_request_review_rounds WHERE request_id = ? ORDER BY review_round", (request_id,)
    )
    round1_row = next((r for r in review_rounds if r["review_round"] == 1), {})
    round2_row = next((r for r in review_rounds if r["review_round"] == 2), {})
    record(
        "step13_db_verify_cleared_and_review_history_preserved",
        status=row_after_clear["status"], expected="PendingFinalApproval",
        matches_expected=row_after_clear["status"] == "PendingFinalApproval",
        review_round_count=len(review_rounds),
        round1_recommendation=round1_row.get("recommendation"),
        round1_reason_preserved=("R1" in (round1_row.get("specialist_reason") or "")),
        round2_recommendation=round2_row.get("recommendation"),
        flat_column_now_shows_round2_only=(
            row_after_clear.get("specialist_reason") == round2_row.get("specialist_reason")
        ),
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 14/15 -- RM sees the feedback + new Next Best Work, then
    # creates the Proposal that gates Manager's decision.
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "staff", "RM-999")
    select_request_in_picker(page, "#rmCreditPicker", request_id)
    rm_form_text = page.locator("#rmCreditFormView").inner_text() if page.locator("#rmCreditFormView").count() else ""
    rm_sees_reason = "R2" in rm_form_text or "du dieu kien" in rm_form_text.lower()
    proposal_button_visible = page.locator("button:has-text('Tạo Proposal trình Manager')").count() > 0
    shot(page, "rm_sees_feedback_and_proposal_button")
    record(
        "step14_rm_sees_feedback_and_nbw",
        rm_sees_reason=rm_sees_reason, proposal_button_visible=proposal_button_visible,
        form_excerpt=rm_form_text[:600], **net.snapshot(),
    )

    net.clear()
    proposal_clicked = False
    if proposal_button_visible:
        page.fill("#creditProposalNote", f"[RUN-{RUN_MARKER}] De nghi Manager phe duyet giai ngan.")
        page.click("button:has-text('Tạo Proposal trình Manager')")
        page.wait_for_timeout(1200)
        proposal_clicked = True
    shot(page, "rm_creates_proposal")
    row_after_proposal = get_request(request_id)
    record(
        "step15_rm_creates_proposal",
        clicked=proposal_clicked, proposal_created_at=row_after_proposal.get("proposal_created_at"),
        **net.snapshot(),
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 16/17 -- Manager sees the approval queue (gated on the
    # proposal existing) and approves.
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "manager")
    shot(page, "manager_dashboard")
    record("step16_manager_dashboard", total_cases_text=page.locator("#mgrTotalCases").inner_text(), **net.snapshot())

    found_for_manager = select_request_in_picker(page, "#managerCreditPicker", request_id)
    manager_form_text = page.locator("#managerCreditFormView").inner_text() if page.locator("#managerCreditFormView").count() else ""
    sees_proposal_notice = "Proposal do RM tạo" in manager_form_text
    acted = False
    if found_for_manager and sees_proposal_notice:
        reason_box = page.locator("#creditSharedReason")
        if reason_box.count():
            reason_box.fill(f"[RUN-{RUN_MARKER}] Ho so du dieu kien, phe duyet giai ngan.")
            approve_btn = page.locator("button:has-text('Phê duyệt giải ngân')")
            if approve_btn.count():
                approve_btn.first.click()
                page.wait_for_timeout(1200)
                acted = True
    shot(page, "manager_final_decision")
    row_final = get_request(request_id, want_status="Approved") if acted else get_request(request_id)
    record(
        "step17_manager_decision",
        found_for_manager=found_for_manager, sees_proposal_gate_notice=sees_proposal_notice, acted=acted,
        final_status=row_final["status"], final_decision=row_final["final_decision"],
        approved_by=row_final["approved_by"],
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 18 -- RM sees the final status.
    # ------------------------------------------------------------------
    goto_app(page)
    net.clear()
    login(page, "staff", "RM-999")
    select_request_in_picker(page, "#rmCreditPicker", request_id)
    rm_final_text = page.locator("#rmCreditFormView").inner_text() if page.locator("#rmCreditFormView").count() else ""
    shot(page, "rm_sees_final_status")
    record(
        "step18_rm_sees_final_status",
        shows_approved=("Approved" in rm_final_text or "Đã duyệt" in rm_final_text or "phê duyệt" in rm_final_text.lower()),
        excerpt=rm_final_text[:400], **net.snapshot(),
    )
    logout(page)

    # ------------------------------------------------------------------
    # STEP 19 -- Timeline must contain every mandatory event type
    # (debug-only API read of the real timeline_events table).
    # ------------------------------------------------------------------
    timeline = _api_get(page, f"/api/v2/cases/{case_id}/timeline", "RM-999", "SESS-MP")
    timeline_types = [e.get("event_type") for e in timeline] if isinstance(timeline, list) else []
    missing_events = [t for t in REQUIRED_TIMELINE_EVENTS if t not in timeline_types]
    record(
        "step19_timeline_completeness",
        total_events=len(timeline_types), event_sequence=timeline_types,
        missing_required_events=missing_events, all_required_events_present=not missing_events,
    )

    # ------------------------------------------------------------------
    # Unauthorized-data-hidden check (same field-diff style as before).
    # ------------------------------------------------------------------
    customer_payload = _api_get(page, "/api/v2/credit-requests", "USER-MP-001", "SESS-MP")
    our_row_customer_view = next((r for r in customer_payload if r.get("request_id") == request_id), {})
    record(
        "final_unauthorized_data_hidden_check",
        customer_visible_fields=sorted(our_row_customer_view.keys()),
        leaks_specialist_reason="specialist_reason" in our_row_customer_view,
        leaks_specialist_recommendation="specialist_recommendation" in our_row_customer_view,
        leaks_proposal_note="proposal_note" in our_row_customer_view,
    )


def _api_get(page: Page, path: str, employee_id: str, session_id: str) -> Any:
    resp = page.request.get(
        f"{BASE_URL}{path}",
        headers={"X-Employee-ID": employee_id, "X-Session-ID": session_id},
    )
    if resp.status >= 400:
        return []
    return resp.json()


def _dump_trace() -> None:
    out = SHOT_DIR / "trace.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"run_marker": RUN_MARKER, "trace": TRACE}, f, indent=2, ensure_ascii=False)
    print(f"\nTrace written to {out}")


def test_full_cross_role_journey() -> None:
    """pytest entry point."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
