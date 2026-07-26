# 24 — Timeline & Notification Verification

## 1. Timeline (bảng `timeline_events`, append-only, KHÔNG suy ra từ state)

Schema thật (migration v3, `app/storage/migrations.py`):
```sql
CREATE TABLE timeline_events (
    event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, event_type TEXT NOT NULL,
    actor_role TEXT NOT NULL, actor_id TEXT NOT NULL, title TEXT NOT NULL,
    description TEXT, entity_type TEXT, entity_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
```

Nơi ghi (tất cả 14 loại event bắt buộc, không thiếu loại nào):

| Event type | Ghi ở đâu | Trigger thật |
| --- | --- | --- |
| `CASE_CREATED` | `router.py:create_sales_case` | Customer/RM tạo case mới |
| `DOCUMENT_UPLOADED` | `router.py:upload_sales_case_documents` | Mỗi file upload (kể cả bản thay thế của customer) |
| `PROFILE_CONFIRMED` | `router.py:confirm_sales_case_profile` | RM xác nhận Customer Business Snapshot |
| `AGENT_ANALYSIS_COMPLETED` | `router.py:run_sales_case_analysis` | Multi-Agent chạy xong |
| `WORK_ITEM_CREATED` | `credit_request_router.py:forward_credit_request`, `employee_router.py:forward_case_to_specialist` | RM forward tờ trình / RM giao case cho chuyên viên |
| `SPECIALIST_REVIEW_SUBMITTED` | `credit_request_router.py:appraise_credit_request` | Mọi lần chuyên viên thẩm định (mọi round) |
| `DOCUMENT_REQUEST_CREATED` | `credit_request_router.py:appraise_credit_request` (khi `needs_more_information`) | |
| `CUSTOMER_DOCUMENT_RESUBMITTED` | `workflow_router.py:submit_document_request` | Khách hàng nộp lại hồ sơ |
| `EVIDENCE_UPDATED` | `workflow_router.py:submit_document_request` | Cùng lúc với trên |
| `WORK_ITEM_REOPENED` | `workflow_router.py:submit_document_request` (qua `reopen_after_resubmission`) | Ngay khi hồ sơ được mở lại cho chuyên viên, KHÔNG đợi tới khi chuyên viên bấm nút |
| `SPECIALIST_REVIEW_CLEARED` | `credit_request_router.py:appraise_credit_request` (khi `recommend`/`not_recommended`) | |
| `PROPOSAL_CREATED` | `credit_request_router.py:create_credit_proposal` | RM tạo proposal |
| `APPROVAL_SUBMITTED` | `credit_request_router.py:decide_credit_request` | Mọi quyết định Manager (kể cả `needs_more_information`) |
| `APPROVAL_COMPLETED` | `credit_request_router.py:decide_credit_request` (khi quyết định là terminal) | |

Đọc: `GET /api/v2/cases/{case_id}/timeline` (mọi role có quyền xem case, kể cả case chỉ tồn tại qua Credit Request mà chưa từng chạy `run-analysis` — có fallback scope-check qua `credit_request_router.list_by_case_id`, xem `workflow_router.py:_case_access`).

**Kết quả chạy thật** (báo cáo 22, `step19`): 17 sự kiện, đủ 14 loại, đúng thứ tự nhân-quả, `missing_required_events: []`.

## 2. Notifications (bảng `notifications`)

Schema thật:
```sql
CREATE TABLE notifications (
    notification_id TEXT PRIMARY KEY, recipient_id TEXT NOT NULL, recipient_role TEXT NOT NULL,
    case_id TEXT, type TEXT NOT NULL, title TEXT NOT NULL, message TEXT NOT NULL,
    route TEXT, read_at TEXT, created_at TEXT NOT NULL
);
```

Trigger đã nối (khớp mục 8 của prompt):

| Trigger | Người nhận | Xác nhận |
| --- | --- | --- |
| RM forward case cho chuyên viên | Chuyên viên | `type=case_forwarded` |
| RM forward tờ trình tín dụng | Credit Specialist | `type=credit_request_forwarded` |
| Chuyên viên yêu cầu bổ sung | Customer + RM | `type=document_requested` (customer), `type=specialist_needs_more_information` (RM) |
| Customer nộp lại hồ sơ | Credit Specialist + RM | `type=customer_resubmitted` — **verify thật** (báo cáo 22 `step10`): `{"recipient_id": "SPEC-CREDIT-001", "type": "customer_resubmitted", ...}` |
| Chuyên viên clear | RM | `type=specialist_cleared` |
| RM tạo proposal | Manager | `type=proposal_ready` |
| Manager quyết định | RM | `type=manager_decision` |

Đọc: `GET /api/v2/me/notifications` (tự động lọc theo `identity.employee_id` của người gọi — không cần tham số), `POST /api/v2/notifications/{id}/read`.

Giao diện: widget chuông "🔔 Thông báo" dưới thanh topbar (mọi role, không ẩn theo role vì backend tự lọc đúng người), số chưa đọc cập nhật realtime sau mỗi hành động (`loadMyNotifications()` được gọi lại sau: forward-to-specialist, appraisal, proposal, decision, login).

**Xác nhận qua UI thật** (báo cáo 22 `step11`): widget hiển thị đúng số lượng chưa đọc (`unread_count_text: "12"` — số cộng dồn từ nhiều lần chạy demo trong phiên, không phải giả).

## 3. Giới hạn còn lại (nói rõ)

- Cơ chế là **polling khi hành động xảy ra** (gọi lại `loadMyNotifications()` sau mỗi action), KHÔNG phải poll định kỳ nền hay WebSocket — đúng như prompt cho phép ("Polling chấp nhận được cho demo. Không cần WebSocket.") nhưng nghĩa là nếu người dùng B gửi thông báo trong khi người dùng A đang ngồi yên trên trang, A sẽ không thấy số mới cho tới khi A tự thao tác hoặc tải lại trang.
- Timeline cho pipeline SalesCase thuần túy (không đi qua Credit Request) mới có 4/14 loại event khả dụng thực tế (`CASE_CREATED/DOCUMENT_UPLOADED/PROFILE_CONFIRMED/AGENT_ANALYSIS_COMPLETED`) — các event còn lại (`WORK_ITEM_CREATED` qua forward-to-specialist, `SPECIALIST_REVIEW_*`, `PROPOSAL_CREATED`, `APPROVAL_*`) chỉ có ý nghĩa đầy đủ trên nhánh Credit Request đã verify hoàn chỉnh; nhánh SalesCase thuần (Proposal Preview → RM approve → execute) chưa được nối timeline trong lần P0 này (xem báo cáo 25, "Rủi ro còn lại").
