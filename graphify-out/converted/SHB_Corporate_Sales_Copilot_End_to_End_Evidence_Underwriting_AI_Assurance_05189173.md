<!-- converted from SHB_Corporate_Sales_Copilot_End_to_End_Evidence_Underwriting_AI_Assurance.docx -->

THIẾT KẾ WORKFLOW HAI CHIỀU
THU THẬP HỒ SƠ, THẨM ĐỊNH & HỖ TRỢ BÁN HÀNG
SHB Corporate Sales Copilot — Existing/New Customer, Underwriting Handoff và AI Assurance


Phiên bản 2.0 • Thiết kế phục vụ MVP/Pilot

# Tóm tắt điều hành
Flow cũ không bị thay thế. Hệ thống vẫn nhận biết nhu cầu, chạy ba Expert Agent, đề xuất sản phẩm, chính sách, quy trình, câu hỏi và hành động tiếp theo cho RM. Phần cải tiến nằm trước và sau flow này:
- Trước khi chạy Agent: nhận diện khách hàng là hiện hữu hay mới và xây Customer/Case Snapshot phù hợp.
- Sau khi ba Agent tạo yêu cầu: hợp nhất thành checklist duy nhất và đối chiếu với evidence inventory đã có.
- Chỉ yêu cầu khách hàng cung cấp phần còn thiếu, hết hạn, mâu thuẫn hoặc chưa đạt mức xác thực.
- Tài liệu mới được kiểm tra nhiều lớp trước khi trở thành Verified Evidence.
- Evidence mới làm thay đổi Snapshot; hệ thống chỉ chạy lại các Agent hoặc node bị ảnh hưởng.
- RM luôn nhìn thấy đồng thời: thông tin khách hàng, sản phẩm có thể bán, chính sách liên quan, quy trình vận hành, checklist hồ sơ và Next Best Work.

# 1. Những gì được giữ nguyên và những gì được bổ sung

# 2. Mô hình hai chiều
## 2.1. Chiều hỗ trợ RM từ ba Expert Agent
Ba Agent không chỉ trả lời bằng văn bản. Mỗi Agent phải xuất cả guidance và yêu cầu dữ liệu/hồ sơ có cấu trúc.

## 2.2. Chiều khách hàng cung cấp và hệ thống thẩm định
- Hệ thống xuất checklist hiện tại trước khi gửi bất kỳ yêu cầu nào.
- Checklist đánh dấu requirement đã được dữ liệu cũ thỏa mãn, cần cập nhật, còn thiếu, cần chữ ký, cần OTP hoặc cần review.
- RM chọn hoặc hệ thống đề xuất gói yêu cầu gửi khách hàng.
- Khách hàng cung cấp tài liệu, form, chữ ký hoặc OTP theo đúng policy.
- Document Assurance Pipeline kiểm tra file, nội dung, đầy đủ, nhất quán, xác thực và chữ ký.
- Chỉ khi đạt policy, tài liệu mới trở thành Verified Evidence.
- Snapshot được tạo version mới và Agent liên quan được chạy lại.
- RM nhận Next Best Work mới để hoàn thành tác vụ.
# 3. Flow tổng thể sau cải tiến

Hình 1. Master workflow: nhận diện khách hàng → phân tích 3 Agent → checklist → evidence → cập nhật RM

# 4. Bước 0 — Customer Resolver và Case Initializer
Ngay khi RM tìm khách hàng hoặc tạo một yêu cầu mới, hệ thống phải xác định đây là existing customer hay new customer. Không dựa duy nhất vào tên; cần resolver theo CIF, mã số thuế, số tài khoản, customer ID, thông tin liên hệ và quyền truy cập của RM.

# 5. Flow A — Khách hàng hiện hữu tại SHB

Hình 2. Existing customer flow: tái sử dụng dữ liệu có kiểm soát trước khi yêu cầu khách hàng bổ sung
## 5.1. Dữ liệu phải tải trước khi chạy Expert Agent
- Customer master: CIF, pháp nhân, mã số thuế, ngành nghề, phân khúc, branch/team phụ trách.
- Sản phẩm đang sử dụng: tài khoản, Internet Banking, payroll, cash management, API, tín dụng, bảo lãnh, thanh toán quốc tế.
- Evidence inventory: hồ sơ pháp lý, KYC/UBO, báo cáo tài chính, hợp đồng, form, file tích hợp và lịch sử xác minh.
- Lifecycle của từng evidence: version, verified_at, valid_to, status, source, owner và reason code.
- Case/history: yêu cầu trước, quyết định, ngoại lệ, review specialist, approval và action đã thực hiện.
- Dữ liệu hành vi nghiệp vụ phù hợp quyền: volume giao dịch, payroll size, collection pattern, nhưng phải theo data access policy.
## 5.2. Checklist phải xuất hiện trước khi liên hệ khách hàng
Với mỗi requirement của yêu cầu mới, Requirement Matcher phải tìm evidence phù hợp trong dữ liệu cũ. Kết quả không phải chỉ là “có/không”, mà là một trạng thái nghiệp vụ.

## 5.3. Kết quả RM phải nhìn thấy

# 6. Flow B — Khách hàng mới

Hình 3. New customer flow: Agent có thể tư vấn sớm nhưng checklist được tạo theo sản phẩm và quy trình
## 6.1. Không chờ đầy đủ hồ sơ mới tư vấn
Với khách hàng mới, hệ thống cần đủ thông tin tối thiểu để hiểu nhu cầu, nhưng không bắt RM thu toàn bộ hồ sơ trước khi Product Agent đưa ra hướng tư vấn sơ bộ. Đầu ra phải phân biệt rõ recommendation sơ bộ và recommendation đã đủ evidence.

## 6.2. Baseline và conditional checklist

# 7. Cách ba Expert Agent tạo thông tin và checklist

Hình 4. Requirement Compiler: hợp nhất yêu cầu của ba Agent và đối chiếu với evidence inventory
## 7.1. Output contract bắt buộc của mỗi Agent
{
"agent": "product_agent | legal_agent | operations_agent",
"guidance": {
"recommendations": [],
"policies": [],
"process_steps": [],
"risks": [],
"next_questions": []
},
"evidence_requirements": [
{
"requirement_code": "FINANCIAL_STATEMENT_LATEST",
"title": "Báo cáo tài chính gần nhất",
"mandatory_level": "required | conditional | optional",
"reason_codes": ["WORKING_CAPITAL_ELIGIBILITY"],
"required_fields": ["reporting_period", "revenue", "profit"],
"freshness_policy_id": "FIN-365D",
"signature_policy_id": null,
"authenticity_policy_id": "DOC-ENHANCED",
"applies_when": {"product_ids": ["PROD-WORKING-CAPITAL"]}
}
]
}
## 7.2. Evidence Requirement Compiler phải làm gì
- Chuẩn hóa requirement_code và document type.
- Gộp requirement trùng giữa Product, Legal và Operations.
- Giữ lại toàn bộ reason_codes và agent_run_refs để giải thích nguồn yêu cầu.
- Áp dụng điều kiện theo sản phẩm, customer type, risk, channel và process step.
- Gắn validation, freshness, signature và authenticity policy.
- Xác định requirement nào là blocker, requirement nào có thể deferred.
- Sinh một checklist duy nhất cho case, không tạo ba checklist rời.
# 8. Evidence inventory và logic tái sử dụng
Evidence inventory là danh mục các bằng chứng mà SHB đang có cho khách hàng, không chỉ là danh sách file. Mỗi evidence phải biết nó chứng minh claim nào, được sinh từ tài liệu nào, còn hiệu lực đến đâu và có thể dùng cho case nào.
EvidenceInventoryItem
- evidence_id
- customer_id
- evidence_type
- supported_claims
- source_artifact_ref
- document_version
- verification_status
- verified_at
- valid_from / valid_to
- freshness_policy_applied
- customer_scope
- product_scope
- case_scope
- signature_assurance
- authenticity_assurance
- conflicts
- superseded_by
## 8.1. Quy tắc không yêu cầu lại hồ sơ
- Requirement và evidence phải cùng loại hoặc có mapping policy hợp lệ.
- Evidence phải còn hiệu lực theo policy của yêu cầu mới, không chỉ theo ngày hết hạn ghi trên giấy.
- Supported claims phải bao phủ đúng trường mà requirement cần.
- Không có conflict chưa xử lý với CRM hoặc evidence mới hơn.
- Signature/authenticity assurance phải đạt mức yêu cầu của case mới.
- Quyền tái sử dụng phải phù hợp tenant, customer, case và mục đích xử lý.
- Nếu requirement mới yêu cầu version mới hơn, evidence cũ chỉ được hiển thị là historical, không được tự coi là đủ.
# 9. Checklist và trạng thái xử lý

# 10. Document Assurance Pipeline
Tài liệu chỉ trở thành Verified Evidence sau khi đi qua các control bắt buộc. Các chiều đánh giá phải độc lập; không được tính điểm trung bình để bù cho một lỗi nghiêm trọng.


# 11. Chữ ký số, chữ ký bản giấy và OTP

# 12. RM Workspace sau cải tiến
RM không nên chuyển qua nhiều màn hình rời để ghép thông tin. Một case workspace cần trình bày theo thứ tự từ hiểu khách hàng đến hành động.

# 13. Customer Request Package
Hệ thống không gửi toàn bộ checklist nội bộ cho khách hàng. Nó phải biên dịch các requirement chưa đạt thành một gói yêu cầu dễ hiểu.
CustomerRequestPackage
- request_id
- case_id
- customer_id
- requested_items[]
- title
- business-friendly reason
- accepted formats
- required fields/pages
- sample/template
- due date
- allowed actions: upload | fill_form | sign | otp
- secure_upload_link
- status
- reminders
- response_events
- Không hiển thị rule nội bộ, fraud score hoặc forensic details nhạy cảm.
- Phải nói rõ phần nào thiếu và cách sửa, ví dụ “thiếu trang chữ ký” thay vì “tài liệu không hợp lệ”.
- Cho phép RM review nội dung trước khi gửi.
- Mọi request và reminder phải idempotent, có audit và expiry.
- Tài liệu khách hàng tải lại tạo version mới; không ghi đè raw artifact.
# 14. Vòng cập nhật ngược về ba Expert Agent
Khi evidence mới được VERIFIED, hệ thống không chạy lại toàn bộ pipeline một cách mù quáng. Impact Analyzer xác định claim, policy, product hoặc process node nào bị thay đổi.


# 15. Metadata và biểu diễn dữ liệu end-to-end
Tất cả requirement, tài liệu, assessment, evidence, snapshot và decision phải đi qua Unified Metadata Plane để có thể kiểm soát và truy ngược.
REQ-001 EvidenceRequirement:v2
├─ requested_by → ARUN-PRODUCT-010
├─ requested_by → ARUN-LEGAL-011
└─ satisfied_by → EVD-008:v3

EVD-008:v3
├─ derived_from → DOC-004:v2
├─ assessed_by → ASSESS-004:v2
├─ supports → customer.ubo_status
└─ included_in → SNAP-CUS-001:v7

SNAP-CUS-001:v7
└─ used_by → ARUN-LEGAL-019 / ARUN-PRODUCT-020 / ARUN-OPS-021

# 16. Ví dụ 1 — Khách hàng hiện hữu yêu cầu vốn lưu động
- RM tìm Công ty Minh Phát theo CIF/MST. Hệ thống xác nhận đây là existing customer.
- Customer Loader hiển thị tài khoản hiện tại, Internet Banking, giấy đăng ký DN đã verified, UBO cũ, BCTC năm trước và case cash management trước đây.
- Khách hàng yêu cầu vốn lưu động và muốn tối ưu thanh toán nhà cung cấp.
- Product Agent đề xuất Working Capital + Bulk Supplier Payment + Cash Management.
- Legal Agent xác định BCTC mới, UBO còn hiệu lực và kiểm tra nợ xấu là requirements.
- Operations Agent đưa ra bước khảo sát dòng tiền, thu file supplier, setup approval matrix và proposal.
- Requirement Matcher xác định giấy đăng ký DN còn hiệu lực nên không yêu cầu lại; BCTC đã quá freshness policy nên REFRESH_REQUIRED; UBO có conflict với thông tin mới nên MANUAL_REVIEW; supplier file là MISSING.
- RM nhìn thấy checklist trước khi liên hệ khách hàng và gửi một gói yêu cầu gồm đúng ba phần cần xử lý.
- Khách hàng upload BCTC, file supplier và xác nhận UBO. Hệ thống thẩm định, tạo Verified Evidence và cập nhật snapshot.
- Chỉ Eligibility/Product vốn và Operations supplier-payment được chạy lại. RM nhận proposal draft và action cần approve.
# 17. Ví dụ 2 — Khách hàng mới cần payroll và cash management
- RM nhập thông tin tối thiểu: tên DN, ngành, khoảng 500 nhân sự, nhu cầu chi lương và quản lý dòng tiền.
- Không có match SHB nên tạo provisional customer.
- Product Agent đề xuất Payroll + Corporate Internet Banking + Cash Management, ghi rõ đây là exploratory recommendation.
- Legal Agent sinh baseline onboarding/KYC checklist.
- Operations Agent sinh quy trình khảo sát payroll, tài khoản nhận lương, phân quyền và kế hoạch triển khai.
- Requirement Compiler gộp thành checklist baseline và conditional; RM thấy ngay bước nào cần làm và giấy tờ nào cần thu.
- Khách hàng upload đăng ký DN và danh sách nhân sự. Hệ thống phát hiện bản scan đăng ký thiếu trang sau nên yêu cầu tải lại đúng trang; danh sách nhân sự được lưu nhưng chỉ được dùng theo privacy policy.
- Khi hồ sơ nền tảng verified, recommendation chuyển từ exploratory sang conditional/evidence-supported tùy mức đủ.
# 18. State model ở mức case readiness
CaseReadiness
- customer_identity_readiness
- product_readiness
- legal_readiness
- operational_readiness
- document_readiness
- signature_readiness
- overall_readiness

overall_readiness không phải trung bình điểm.
Một domain blocker bắt buộc => overall = NOT_READY.

# 19. API và service boundary đề xuất

# 20. Acceptance criteria nghiệp vụ
- Existing customer phải hiển thị dữ liệu và hồ sơ đã có trước khi yêu cầu upload mới.
- Không yêu cầu lại evidence còn hiệu lực và đạt policy cho case mới.
- Mỗi sản phẩm đề xuất phải hiển thị điều kiện, chính sách, quy trình và requirement liên quan.
- New customer vẫn nhận được product guidance sớm, nhưng trạng thái evidence phải minh bạch.
- Checklist phải là một object có version, không phải text tự do.
- Requirement phải biết Agent nào yêu cầu và vì sao.
- Tài liệu upload không tự trở thành evidence.
- Mọi document status phải có reason code và next action.
- Evidence mới chỉ chạy lại node bị ảnh hưởng.
- RM approval/action flow cũ vẫn giữ nguyên và không bị bypass.
- Mọi thay đổi phải có metadata, lineage, version và audit.
# 21. Lộ trình triển khai

# 22. Intent chuẩn để AI triển khai

# 23. Kết luận
Thiết kế mới không biến sản phẩm thành một hệ thống chỉ thu hồ sơ. Nó biến flow bán hàng hiện tại thành một vòng lặp có kiểm soát giữa tư vấn và evidence:
Hiểu khách hàng và yêu cầu
→ Đề xuất sản phẩm/chính sách/quy trình
→ Xác định requirement
→ Tái sử dụng evidence SHB đã có
→ Thu đúng phần còn thiếu
→ Thẩm định và xác minh
→ Cập nhật Agent và readiness
→ Hỗ trợ RM hoàn thành tác vụ
# 24. Flow tổng thể hoàn chỉnh sau cải tiến

Hình 5. Dữ liệu khách hàng → 3 Agent → evidence → RM duyệt gửi → thẩm định

# 25. Submission Readiness trước khi RM được bấm duyệt

# 26. Ý nghĩa của thao tác RM duyệt khách hàng

RMSubmissionApproval
- approval_id
- case_ref + expected_case_version
- submission_ref + expected_submission_version
- customer_snapshot_ref
- package_hash
- approved_sections
- acknowledged_warnings
- actor_employee_id / role_id
- approved_at / expires_at
# 27. Handoff sang bộ phận thẩm định

Hình 6. RM duyệt package → thẩm định → yêu cầu bổ sung/resubmit → quyết định
1. Hệ thống tạo Submission Preview từ dữ liệu đã freeze.
2. RM đọc Executive Summary, Product/Policy/Operations views, Evidence Matrix, conflict và warning.
3. RM duyệt package hash và exact versions.
4. Hệ thống tạo Underwriting Submission version bất biến và Source Manifest.
5. Submission vào underwriting queue với owner, SLA, product scope, priority và risk tier.
6. Underwriter đọc Executive View rồi drill-down tới Evidence, source document, page/region, version và lineage.
7. Nếu cần bổ sung, Underwriter tạo Information Request có requirement code, reason, recipient và due date.
8. Dữ liệu bổ sung quay lại Document Assurance, tạo Evidence/Snapshot/Submission version mới.
9. Diff View cho biết field, evidence, rule result, risk và condition nào thay đổi.
10. Underwriter phát hành APPROVED, CONDITIONALLY_APPROVED hoặc REJECTED với reasons, conditions, validity và source refs.
11. RM nhận Next Best Work; action chỉ mở khi decision và conditions cho phép.
# 28. Gói thông tin gửi thẩm định
Gói thẩm định dùng cùng một submission snapshot nhưng có hai lớp: trình bày dễ hiểu và metadata/lineage để truy xuất, can thiệp, kiểm tra nguồn và audit.

## 28.1. Underwriting Submission schema
{
"submission_id": "UWS-001",
"submission_version": 2,
"state": "sent_to_underwriting",
"case_ref": {"case_id": "CASE-001", "case_version": 14},
"customer_snapshot_ref": {"meta_id": "SNAP-001", "version": 7},
"requested_decision": {
"decision_type": "working_capital_assessment",
"product_ids": ["PROD-WORKING-CAPITAL"],
"scope": "eligibility_and_conditions"
},
"executive_summary": {
"customer_overview": "...",
"request_overview": "...",
"recommendation_overview": "...",
"key_risks": [],
"outstanding_conditions": []
},
"section_refs": {
"product_outputs": [],
"policy_evaluations": [],
"operational_readiness": [],
"evidence_matrix": [],
"conflicts": [],
"exceptions": []
},
"source_manifest_ref": {"meta_id": "SOURCE-MANIFEST-001", "version": 2},
"package_hash": "sha256:...",
"approved_for_submission_by": "EMP-RM-001"
}
# 29. Unified Metadata Plane từ đầu đến cuối

Hình 7. Metadata thống nhất từ raw input tới underwriting decision và action

## 29.1. Metadata envelope bắt buộc
MetadataEnvelope
- meta_id / meta_type / schema_name / schema_version
- tenant_id / branch_id / team_id
- trace_id / correlation_id / case_id / customer_id
- actor: customer | employee | agent | tool | underwriter
- source: artifact/document/page/span/connector
- typed payload
- processing: processor/model/prompt/policy/catalog/SOP versions
- quality: confidence, validation, conflicts, reviewer
- lineage: parent refs, relations, root artifact
- security: classification, access scopes, masks, retention
- lifecycle: status, object_version, validity
- integrity: content_hash, previous_hash, idempotency_key
- timestamps
- Không update đè payload cũ; mọi thay đổi tạo version/revision mới.
- Mọi Agent run pin exact Customer Snapshot, Employee Context, Evidence, catalog, policy và SOP versions.
- RM duyệt package hash cụ thể; package thay đổi làm approval cũ mất hiệu lực.
- Underwriting decision pin đúng submission version.
- Mọi action truy ngược được tới decision, approval, Agent output, Evidence và raw artifact.
- Metadata Access Service query theo case/customer/employee/source/version và ghi access log.
- Validator/guardrail can thiệp tại từng stage giống probe trong pipeline.
## 29.2. Metadata types cho thẩm định

# 30. Retrieval architecture để hạn chế hallucination
Mỗi Agent dùng Controlled Retrieval Plane. LLM không trả lời từ trí nhớ mô hình; nó chỉ tổng hợp Grounding Pack đã lọc theo role, scope, authority, version, freshness và applicability.

## 30.1. Retrieval pipeline
1. Resolve identity, role, customer/case scope và purpose of use.
2. Planner tạo structured retrieval plan.
3. Exact metadata/key lookup trước; semantic retrieval sau.
4. Filter tenant/customer/case/effective date/version.
5. Rerank theo authority, applicability, freshness và relevance.
6. Deduplicate và detect conflicts.
7. Tạo Grounding Pack có source_id, version, page/span, quote, authority tier và validation state.
8. Agent chỉ nhận context tối thiểu theo role.
9. Output tham chiếu grounding_item_ids; citation validator kiểm tra lại.
10. Nếu retrieval lỗi hoặc không đủ, Agent abstain/ask/request evidence; không suy đoán.
## 30.2. Source tiers

# 31. Guardrail nhiều lớp

Hình 8. Retrieval, guardrail, human review và evaluation bao quanh mọi Agent

## 31.1. Structured Agent output
{
"agent_run_id": "ARUN-...",
"agent_type": "product | legal | operations",
"input_snapshot_refs": [],
"retrieval_plan_ref": {},
"grounding_item_refs": [],
"facts_used": [],
"inferences": [],
"recommendations": [],
"requirements": [],
"risks": [],
"missing_information": [],
"abstentions": [],
"citations": [],
"confidence": {"overall": 0.0, "basis": "evidence_coverage"},
"guardrail_results": [],
"model_provider": "...",
"model_name": "...",
"prompt_version": "..."
}

# 32. Đánh giá từng Agent và module

## 32.1. Evaluation dataset và hard gates
- Dataset có existing/new customer, simple/multi-product, missing info, legal block, operations dependency, out-of-scope và adversarial injection.
- Có evidence cũ còn hiệu lực, hết hạn, conflict, duplicate, partial, signature pending và authenticity suspected.
- Có underwriting approved/conditional/rejected/information-request/resubmission.
- Offline deterministic tests tách khỏi live-model evaluation; ghi model/prompt/source versions.
- Cold-cache và warm-cache; infrastructure errors tách quality failures.
- Human review sample cho summary faithfulness và policy interpretation.
- Critical safety metric không được giảm dù average score tăng.

# 33. Submission state machine
DRAFT
→ READY_FOR_RM_REVIEW
→ RM_APPROVED
→ SUBMISSION_FROZEN
→ SENT_TO_UNDERWRITING
→ UNDER_REVIEW
→ INFORMATION_REQUESTED
→ RESUBMISSION_READY
→ RESUBMITTED
→ UNDER_REVIEW
→ APPROVED | CONDITIONALLY_APPROVED | REJECTED | WITHDRAWN

- Resubmission tạo version mới.
- Decision pin một submission version.
- Package thay đổi làm RM approval cũ invalid.
- Information Request không sửa submission cũ.
- Underwriting Decision không tự execute action.
# 34. API và database bổ sung
## 34.1. API
GET  /api/v2/cases/{case_id}/submission-readiness
POST /api/v2/cases/{case_id}/submissions/prepare
GET  /api/v2/cases/{case_id}/submissions/{submission_id}/preview
POST /api/v2/cases/{case_id}/submissions/{submission_id}/approve
POST /api/v2/submissions/{submission_id}/send

GET  /api/v2/underwriting/queue
GET  /api/v2/underwriting/submissions/{submission_id}
GET  /api/v2/underwriting/submissions/{submission_id}/lineage
GET  /api/v2/underwriting/submissions/{submission_id}/diff
POST /api/v2/underwriting/submissions/{submission_id}/assign
POST /api/v2/underwriting/submissions/{submission_id}/information-requests
POST /api/v2/underwriting/submissions/{submission_id}/reviews
POST /api/v2/underwriting/submissions/{submission_id}/decision
## 34.2. Database/Event Store

# 35. Acceptance criteria end-to-end
- Existing customer hiển thị dữ liệu/evidence đã có trước khi yêu cầu mới.
- New customer nhận recommendation sơ bộ nhưng không bị trình bày như đã đủ điều kiện.
- Ba Agent chỉ dùng Grounding Pack và output có schema/source refs.
- Checklist không yêu cầu lại evidence còn hiệu lực.
- Tài liệu phải qua Document Assurance trước khi thành Evidence.
- Nút gửi thẩm định chỉ mở khi Submission Readiness đạt.
- RM duyệt package hash/exact versions, không phát hành underwriting decision.
- Underwriter nhận Executive View dễ đọc và drill-down được nguồn/metadata/lineage.
- Information Request tạo resubmission version mới.
- Decision có outcome/reasons/conditions/validity/source refs và pin đúng version.
- Guardrail chặn unsupported claim, invalid evidence, stale version, unauthorized action và injection.
- Mỗi Agent có evaluation riêng và hard safety gates.
- Action cuối truy ngược được tới raw artifact, evidence, Agent output, RM submission approval và underwriting decision.
# 36. Intent chuẩn để AI triển khai

# 37. Flow kết luận
Customer Resolution
→ Existing Data Reuse / New Customer Intake
→ Controlled Retrieval
→ Product + Legal/Policy + Operations Agents
→ Guardrail & Evidence Validation
→ Dynamic Checklist
→ Customer Evidence Collection
→ Document Assurance
→ Verified Evidence + Snapshot
→ RM Submission Approval
→ Underwriting Case Packet
→ Underwriting Review / Information Request / Decision
→ RM Next Best Work
→ Approved Action under policy
→ Evaluation, Metadata, Audit and Replay
| Mục tiêu tài liệu
Giữ nguyên flow bán hàng hiện tại của Product, Legal/Policy và Operations Agent; bổ sung lớp nhận diện khách hàng, tái sử dụng dữ liệu/hồ sơ đã có, sinh checklist động, thu thập phần còn thiếu, thẩm định tài liệu và cập nhật ngược lại cho ba Expert Agent. |
| --- |
| Nguyên tắc cốt lõi
“Có file” không đồng nghĩa “đủ hồ sơ”. “Khách hàng đã từng giao dịch với SHB” cũng không đồng nghĩa mọi dữ liệu cũ còn hợp lệ cho yêu cầu mới. Hệ thống phải kiểm tra applicability, freshness, completeness, consistency, authenticity và signature policy trước khi tái sử dụng. |
| --- |
| Thành phần | Giữ nguyên | Cải tiến bổ sung |
| --- | --- | --- |
| Intent & Task Understanding | Nhận biết yêu cầu của khách hàng và tác vụ RM cần xử lý. | Bổ sung customer type, case history và dữ liệu sẵn có vào context. |
| Product Agent | Đề xuất sản phẩm/bundle và lý do phù hợp. | Xuất thêm product-specific evidence requirements và policy references. |
| Legal/Policy Agent | Kiểm tra điều kiện, hồ sơ, rủi ro, missing information. | Phân loại evidence có thể tái sử dụng, cần làm mới, cần chữ ký hoặc human review. |
| Operations Agent | Sinh quy trình, checklist, task và đề xuất hành động. | Gắn từng bước vận hành với hồ sơ, owner, dependency, SLA và readiness. |
| RM Approval & Action | RM vẫn là người duyệt và thực hiện action. | Chỉ cho phép action khi required evidence đạt trạng thái policy cho phép. |
| Document Intake | Đọc và trích xuất tài liệu. | Mở rộng thành lifecycle: requirement → request → receive → assure → verify → reuse. |
| Agent | Thông tin hiển thị cho RM | Evidence requirement sinh ra |
| --- | --- | --- |
| Product Agent | Sản phẩm có thể bán, bundle, value proposition, điều kiện thương mại chưa xác định. | Dữ liệu quy mô, dòng tiền, số lượng giao dịch, ERP, nhu cầu vốn, thông tin sử dụng sản phẩm. |
| Legal/Policy Agent | Chính sách, điều kiện, hạn chế, ngoại lệ, lý do blocked/conditional. | Đăng ký DN, đại diện, UBO/KYC, tài liệu tài chính, văn bản ủy quyền, chữ ký/chấp thuận. |
| Operations Agent | Quy trình vận hành, bước triển khai, phụ thuộc, SLA, task owner. | Form đăng ký, file tích hợp, danh sách nhân sự/tài khoản, hợp đồng, checklist readiness. |
| Điểm cần AI hiểu đúng
Flow không bắt đầu bằng việc yêu cầu khách hàng upload lại toàn bộ hồ sơ. Flow bắt đầu bằng việc nhận diện khách hàng, tải dữ liệu hiện có, tạo checklist và chỉ yêu cầu phần còn thiếu hoặc không còn dùng được. |
| --- |
| Kết quả resolver | Ý nghĩa | Hành động hệ thống |
| --- | --- | --- |
| EXISTING_CONFIRMED | Khớp chắc chắn với khách hàng đã có trong SHB. | Load Customer 360, hồ sơ/evidence, sản phẩm, case, approval và expiry. |
| EXISTING_POSSIBLE_MATCH | Có ứng viên nhưng chưa đủ chắc chắn. | Yêu cầu RM chọn/xác nhận; không tự merge customer. |
| NEW_CUSTOMER | Không tìm thấy match đủ tin cậy. | Tạo provisional customer và baseline onboarding context. |
| ACCESS_DENIED | Khách hàng tồn tại nhưng RM không có scope. | Không lộ dữ liệu; hướng dẫn quy trình xin phân công/quyền. |
| DUPLICATE_SUSPECTED | Có nhiều record có thể là cùng một pháp nhân. | Tạo data-quality review, không tự chọn record. |
| Trạng thái | Diễn giải | RM cần làm gì |
| --- | --- | --- |
| SATISFIED_VERIFIED | Đã có evidence đúng loại, còn hiệu lực và dùng được cho yêu cầu mới. | Không yêu cầu lại; hiển thị nguồn và ngày xác minh. |
| SATISFIED_WITH_EXCEPTION | Đã có nhưng đang dựa trên exception/waiver còn hiệu lực. | Hiển thị điều kiện và người phê duyệt exception. |
| REUSABLE_PENDING_CONFIRMATION | Có dữ liệu nhưng cần RM xác nhận applicability cho case mới. | Xác nhận hoặc chuyển review. |
| REFRESH_REQUIRED | Đã có nhưng hết hạn hoặc freshness policy không đạt. | Yêu cầu bản cập nhật. |
| INCOMPLETE_EXISTING | Đã có tài liệu nhưng thiếu trường/trang/chữ ký. | Yêu cầu đúng phần thiếu, không yêu cầu toàn bộ nếu policy cho phép. |
| CONFLICTING_EXISTING | Dữ liệu cũ mâu thuẫn với CRM hoặc tài liệu khác. | Chuyển review/yêu cầu nguồn mới. |
| MISSING | Chưa có evidence phù hợp. | Gửi yêu cầu khách hàng cung cấp. |
| NOT_APPLICABLE | Requirement không áp dụng cho sản phẩm/case này. | Không hiển thị như blocker. |
| Khối giao diện | Nội dung |
| --- | --- |
| Customer Overview | Thông tin doanh nghiệp đã có, nguồn, thời điểm cập nhật, độ tin cậy và cảnh báo conflict. |
| Existing Relationship | Sản phẩm đang dùng, case đang mở, doanh thu/giao dịch liên quan theo quyền truy cập. |
| New Request | Yêu cầu mới đã được chuẩn hóa thành intent, mục tiêu và phạm vi. |
| Product Opportunities | Sản phẩm/bundle có thể bán, lý do, điều kiện, dữ liệu còn thiếu. |
| Policy & Eligibility | Chính sách áp dụng, trạng thái eligible/conditional/blocked/review, nguồn policy. |
| Operational Journey | Các bước cần làm, owner, dependency, SLA, readiness. |
| Evidence Checklist | Requirement, evidence hiện có, status, expiry, missing, signature/review và next action. |
| Next Best Work | Việc RM nên làm tiếp theo, ước lượng thời gian, lý do ưu tiên và action có thể tạo. |
| Mức đầu ra | Điều kiện | Cách hiển thị |
| --- | --- | --- |
| Exploratory Recommendation | Chỉ có nhu cầu và thông tin doanh nghiệp cơ bản. | “Sản phẩm tiềm năng”; không khẳng định eligibility. |
| Conditional Recommendation | Có một phần evidence nhưng còn thiếu requirement quan trọng. | Hiển thị điều kiện và checklist blocker. |
| Evidence-Supported Recommendation | Evidence bắt buộc đã verified ở mức policy yêu cầu. | Có thể chuyển proposal/approval theo workflow. |
| Not Supported / Abstain | Thiếu dữ liệu cốt lõi, xung đột hoặc ngoài phạm vi. | Không bịa; hỏi câu tiếp theo hoặc chuyển người review. |
| Lớp | Ví dụ | Nguồn sinh requirement |
| --- | --- | --- |
| Baseline identity | Đăng ký DN, MST, đại diện, địa chỉ, người liên hệ. | Customer onboarding policy. |
| KYC/UBO | Chủ sở hữu hưởng lợi, thông tin định danh, cấu trúc sở hữu. | Legal/Compliance policy. |
| Product-specific | BCTC cho vốn, danh sách nhân sự cho payroll, file mapping cho API. | Product Agent + catalog/policy. |
| Operational | Form đăng ký, đầu mối kỹ thuật, phân quyền ký duyệt, kế hoạch triển khai. | Operations Agent + SOP. |
| Signature/consent | Hợp đồng, xác nhận thông tin, OTP hoặc chữ ký số. | Signature policy + document type. |
| Risk-driven | Nguồn bổ sung khi có conflict, authenticity signal hoặc risk cao. | Risk/Document Assurance policy. |
| Nhóm trạng thái | State | Ý nghĩa |
| --- | --- | --- |
| Chưa thu thập | REQUIRED / REQUESTED | Requirement áp dụng và đã hoặc chưa gửi yêu cầu. |
| Đã nhận | RECEIVED / PROCESSING | File đã tới nhưng chưa được đánh giá đầy đủ. |
| Không đạt kỹ thuật | UNREADABLE / WRONG_TYPE / MALWARE_QUARANTINED | Không thể dùng; cần tải lại hoặc xử lý bảo mật. |
| Không đạt nội dung | INCOMPLETE / INCONSISTENT / EXPIRED | Thiếu trường, mâu thuẫn hoặc quá hạn. |
| Cần xác thực | AUTHENTICITY_SUSPECTED / SIGNATURE_PENDING / OTP_PENDING | Cần bước kiểm soát bổ sung. |
| Cần người xử lý | MANUAL_REVIEW | Không được auto-verify. |
| Hoàn tất | VERIFIED | Đủ policy và có thể dùng làm evidence. |
| Kết thúc khác | REJECTED / WAIVED / SUPERSEDED / NOT_APPLICABLE | Có lý do, actor, version và audit. |
| Control | Câu hỏi kiểm soát | Output chính |
| --- | --- | --- |
| File security | File có đúng MIME/magic bytes, không malware, không archive bomb? | PASS / QUARANTINED / REJECTED |
| Readability | Có đọc được text, bảng, trang, chữ ký/stamp region? | OCR quality, unreadable pages |
| Document type | Đúng loại giấy tờ mà requirement yêu cầu? | type + confidence + review |
| Field completeness | Đủ trường/trang/phụ lục bắt buộc? | missing_fields |
| Semantic validity | Ngày, số, quan hệ và format có hợp lý? | rule results |
| Cross-document consistency | Tên, MST, đại diện, UBO, tài khoản có khớp? | conflicts |
| Authenticity risk | Có tín hiệu chỉnh sửa, ghép, AI-generated hoặc template bất thường? | risk signals, không kết luận tuyệt đối |
| Signature assurance | Chữ ký/OTP/certificate có đúng policy và bind đúng document hash? | verified/pending/failed |
| Freshness | Tài liệu có còn đủ mới cho yêu cầu hiện tại? | valid/refresh_required |
| Giới hạn cần ghi rõ
Lớp phát hiện tài liệu bị chỉnh sửa hoặc AI tạo chỉ sinh risk signals. Không dùng một model duy nhất để kết luận giấy tờ giả. Trường hợp rủi ro cao phải chuyển Fraud/Legal Reviewer hoặc yêu cầu nguồn chính thức khác. |
| --- |
| Phương thức | Có thể dùng khi | Yêu cầu kiểm soát |
| --- | --- | --- |
| Digital signature/certificate | Document policy chấp nhận và provider hỗ trợ. | Verify certificate, chain, signer identity, signed hash, timestamp. |
| Electronic signature provider | Được policy/pháp lý cho phép. | Provider callback, audit trail, signer identity, payload hash. |
| Wet signature scan | Policy cho phép bản scan chữ ký tay. | Manual review, authenticity signal, representative match. |
| OTP confirmation | Chỉ với loại xác nhận mà policy cho phép; không mặc định là chữ ký số. | Bind case + customer + document version + document hash + expiry + attempts. |
| Dual approval | Tác vụ yêu cầu nhiều người đại diện hoặc nhiều cấp. | Mỗi signer/approver có event và phạm vi riêng. |
| Khu vực | Nội dung bắt buộc | Câu hỏi RM được trả lời |
| --- | --- | --- |
| Customer 360 | Thông tin hiện có, source, freshness, conflict, relationship. | Khách hàng này là ai và SHB đã biết gì? |
| Request Summary | Yêu cầu mới, intent, constraints, desired outcome. | Khách hàng đang cần gì? |
| Product Recommendations | Sản phẩm/bundle, lý do, confidence, điều kiện. | Có thể bán gì và tại sao? |
| Policy & Eligibility | Chính sách, rule, legal status, human review. | Có được làm không và còn vướng gì? |
| Operational Journey | Bước, owner, dependency, SLA, checklist. | Phải làm theo trình tự nào? |
| Evidence Readiness | Đã có/thiếu/hết hạn/conflict/ký/review. | Hồ sơ hiện đã đủ đến đâu? |
| Customer Requests | Gói yêu cầu đã gửi, due date, reminder, response. | Khách hàng đang nợ tài liệu gì? |
| Next Best Work | Task ưu tiên, action, draft, approval. | Tôi nên làm gì tiếp theo để xử lý nhanh nhất? |
| Evidence mới | Node cần chạy lại | Node không nhất thiết chạy lại |
| --- | --- | --- |
| BCTC mới | Financial extraction, Eligibility vốn, Product recommendation vốn, Operations liên quan. | KYC nếu không có field liên quan. |
| UBO đã xác minh | Legal/Eligibility, Risk Gate, affected approval readiness. | Product fit thuần giao dịch nếu không phụ thuộc UBO. |
| Danh sách nhân sự | Payroll Product/Operations checklist. | Working-capital eligibility. |
| Hợp đồng đã ký | Signature verification, Operations readiness, Approval/Action gate. | Document classification của hồ sơ pháp lý khác. |
| ERP mapping file | API Banking Product/Operations. | Legal identity trừ khi file gây conflict. |
| Yêu cầu kỹ thuật
Mỗi Agent run phải pin Customer Snapshot version, Employee Context version, policy/catalog version và evidence refs. Khi dữ liệu thay đổi, tạo workflow resume/re-analysis run mới; không sửa ngược output cũ. |
| --- |
| Metadata type | Mục đích |
| --- | --- |
| evidence_requirement | Mô tả cái cần thu thập, vì sao cần và policy áp dụng. |
| case_checklist_item | Trạng thái requirement trong một case cụ thể. |
| raw_artifact | File gốc bất biến và thông tin upload. |
| document | Tài liệu đã parse/classify theo version. |
| extracted_fact | Field có provenance, confidence và validation. |
| document_assessment | Kết quả từng control kỹ thuật/nghiệp vụ. |
| authenticity_signal | Tín hiệu rủi ro theo vùng/trang/model/tool. |
| signature_request / otp_verification | Bằng chứng consent/signing bind với hash. |
| evidence | Bằng chứng đã được policy cho phép sử dụng. |
| customer_snapshot | Trạng thái khách hàng tại một thời điểm. |
| agent_run / decision / approval / action | Lineage từ dữ liệu tới hành động. |
| Domain | READY khi | BLOCKED/PENDING khi |
| --- | --- | --- |
| Customer identity | Pháp nhân và customer match đã xác nhận. | Duplicate, identity conflict hoặc thiếu baseline. |
| Product | Đủ dữ liệu để giải thích product fit ở mức yêu cầu. | Thiếu dữ liệu cốt lõi hoặc out-of-scope. |
| Legal | Required legal evidence verified hoặc exception hợp lệ. | Rule fail, conflict, expired hoặc human review. |
| Operations | Các dependency và checklist bắt buộc đã đạt. | Thiếu form, mapping, owner hoặc readiness item. |
| Document | Mọi required document controls đạt policy. | Unreadable, incomplete, authenticity suspected. |
| Signature | Required signature/OTP verified và bind đúng hash. | Pending, failed hoặc document version thay đổi. |
| Service | API/Function chính | Trách nhiệm |
| --- | --- | --- |
| Customer Resolver | resolve_customer() | Nhận diện existing/new/possible match và enforce scope. |
| Context Loader | build_customer_snapshot() | Tập hợp dữ liệu/evidence hiện có theo version. |
| Expert Orchestrator | run_product/legal/operations() | Chạy flow cũ trên snapshot chuẩn. |
| Requirement Compiler | compile_requirements() | Gộp, chuẩn hóa và policy hóa checklist. |
| Evidence Inventory | match_requirements() | Tái sử dụng dữ liệu cũ có kiểm soát. |
| Customer Request | create/send/request_package() | Gửi đúng phần thiếu và theo dõi phản hồi. |
| Document Assurance | assess_document() | Parse, extract, validate, authenticity, signature. |
| Evidence Service | create_verified_evidence() | Chỉ tạo evidence khi policy đạt. |
| Impact Analyzer | impacted_nodes() | Xác định phần workflow cần chạy lại. |
| RM Workspace API | get_case_workspace() | Trả Customer 360 + sales + policy + process + checklist + NBW. |
| Giai đoạn | Phạm vi | Kết quả nhìn thấy |
| --- | --- | --- |
| Phase 1 — Existing data first | Customer Resolver, Customer Snapshot, Evidence Inventory, checklist mapping. | RM thấy dữ liệu cũ và phần còn thiếu trước khi liên hệ khách hàng. |
| Phase 2 — Dynamic requirements | Agent output contract + Requirement Compiler + policy mapping. | Checklist sinh theo sản phẩm/chính sách/quy trình. |
| Phase 3 — Customer collection | Request package, upload portal, reminders, versioned artifacts. | Thu đúng hồ sơ thiếu và theo dõi hai chiều. |
| Phase 4 — Document assurance | OCR, completeness, consistency, freshness, authenticity signals, manual review. | Tài liệu được đánh giá trước khi dùng. |
| Phase 5 — Signature/OTP | Provider adapters, hash binding, callback verification. | Hợp đồng/xác nhận đi qua policy. |
| Phase 6 — Impacted re-analysis | Snapshot versioning, impact analyzer, selective agent rerun. | Agent và NBW tự cập nhật khi evidence mới verified. |
| Prompt intent cốt lõi
Hãy giữ nguyên workflow bán hàng hiện có của SHB Corporate Sales Copilot, gồm nhận biết nhu cầu, Product Agent, Legal/Policy Agent, Operations Agent, evidence validation, approval và action. Không thay thế flow này. Hãy bổ sung một lớp customer resolution, existing-data reuse và evidence lifecycle ở xung quanh flow. Khi RM tìm một khách hàng hiện hữu, hệ thống phải tải và hiển thị dữ liệu, sản phẩm, hồ sơ, evidence, case và trạng thái hiệu lực đã có trước; sau đó chạy ba Expert Agent trên yêu cầu mới, sinh product guidance, policy, process steps và evidence requirements. Requirement Compiler hợp nhất yêu cầu của ba Agent thành một checklist duy nhất rồi đối chiếu với evidence inventory. Requirement đã được evidence còn hiệu lực thỏa mãn phải được đánh dấu verified/reusable và không yêu cầu khách hàng cung cấp lại. Requirement đã có nhưng hết hạn, thiếu trường, mâu thuẫn hoặc không đạt authenticity/signature policy phải được đánh dấu refresh/review. Chỉ requirement thật sự thiếu mới được đưa vào customer request package. Với khách hàng mới, hệ thống tạo provisional customer, nhận biết yêu cầu, vẫn đưa ra product recommendation ở mức exploratory/conditional, đồng thời sinh baseline và product-specific checklist theo chính sách và quy trình vận hành. Tài liệu khách hàng cung cấp phải qua Document Assurance Pipeline trước khi trở thành Verified Evidence. Evidence mới tạo Customer Snapshot version mới và chỉ chạy lại Agent/node bị ảnh hưởng. RM Workspace phải hiển thị trong một màn hình: dữ liệu khách hàng đã có, yêu cầu mới, sản phẩm có thể bán, chính sách, quy trình, checklist hồ sơ, trạng thái xác thực, người chịu trách nhiệm và Next Best Work. Mọi requirement, artifact, assessment, evidence, snapshot, agent run, decision, approval và action phải có metadata, version, lineage, quyền truy cập và audit. |
| --- |
| Điểm cần hiểu đúng
Flow bán hàng cũ vẫn giữ nguyên. Phần mới là tái sử dụng dữ liệu SHB đã có, kiểm soát checklist/evidence, rồi tạo handoff chính thức sang bộ phận thẩm định khi RM duyệt đúng gói hồ sơ và đúng phiên bản dữ liệu. |
| --- |
| Nhóm điều kiện | Yêu cầu |
| --- | --- |
| Customer resolution | Khách hàng đã resolve chắc chắn; không còn duplicate/possible match; RM có đúng customer scope. |
| Checklist | Mọi requirement bắt buộc là VERIFIED, WAIVED hợp lệ hoặc CONDITIONALLY_ACCEPTED theo policy. |
| Document assurance | Không còn malware, unreadable blocker, authenticity high-risk chưa review, signature/OTP bắt buộc đang pending. |
| Agent consistency | Product, Legal/Policy và Operations dùng cùng Customer Snapshot, Evidence, catalog, policy và SOP versions. |
| Grounding | Mọi claim trọng yếu có source/evidence refs; claim chưa đủ ghi INSUFFICIENT_EVIDENCE. |
| Risk | Không còn absolute blocker; exception/human review có actor, findings, sources và audit. |
| RM preview | RM đã xem tóm tắt, checklist, evidence matrix, conflict, điều kiện và phạm vi gửi. |
| Integrity | expected_case_version và submission_draft_version khớp; package_hash đã được tính. |
| Không phải phê duyệt tín dụng
Nút “Duyệt khách hàng để gửi thẩm định” chỉ xác nhận RM đã kiểm tra gói hồ sơ và đồng ý gửi đúng package hash, Customer Snapshot version, Evidence versions và phạm vi yêu cầu. RM không được tự phát hành underwriting decision hoặc mở action cuối. |
| --- |
| View | Nội dung | Mục đích |
| --- | --- | --- |
| Executive View | Customer overview, quan hệ SHB, yêu cầu mới, sản phẩm, key risks, readiness, conditions, requested decision. | Nắm tình hình nhanh. |
| Product View | Product/bundle, fit rationale, assumptions, product policy refs, dữ liệu còn thiếu. | Hiểu đề xuất bán hàng. |
| Legal/Policy View | Rule/policy results, blockers, reviewability, exceptions, citations. | Hiểu điều kiện và rủi ro. |
| Operations View | Process steps, dependencies, owner, SLA, readiness. | Hiểu khả năng triển khai. |
| Evidence Matrix | Requirement → Evidence → Claims → freshness → authenticity → signature → reviewer. | Biết kết luận dựa vào đâu. |
| Source View | File, version, page, section, text span/bounding box, quote, connector ref. | Đọc nguồn trực tiếp. |
| Lineage View | Raw artifact → document → fact → assessment → evidence → snapshot → agent → submission. | Truy vết end-to-end. |
| Diff View | Khác biệt giữa submission versions. | Review nhanh khi resubmit. |
| Audit View | Actor, action, timestamp, hash, override và access events. | Giải trình. |
| DeepStream concept | Biểu diễn trong hệ thống | Ý nghĩa |
| --- | --- | --- |
| GstBuffer | Raw artifact, form, message, connector payload | Dữ liệu gốc bất biến. |
| NvDsBatchMeta | Workflow run, case processing run, underwriting submission | Một execution có trace_id và pinned versions. |
| NvDsFrameMeta | Document/page/interaction metadata | Đơn vị nội dung có source/time/version. |
| NvDsObjectMeta | Extracted fact, requirement, evidence, risk signal, decision item | Object có ID/type/status/confidence. |
| NvDsUserMeta | Role, policy, access, signature, review, exception | Metadata nghiệp vụ có schema. |
| Object tracking | Logical object + version history | Theo dõi field/evidence/submission qua revision. |
| Pad probe | Validator, retrieval gate, guardrail, audit hook | Can thiệp tại checkpoint. |
| Broker payload | Canonical metadata event | DB/Event Store vẫn là source of truth. |
| meta_type | Vai trò |
| --- | --- |
| submission_readiness_assessment | Giải thích case đã/chưa đủ điều kiện gửi. |
| rm_submission_approval | RM duyệt version, scope và package hash. |
| underwriting_submission | Logical submission có nhiều version. |
| submission_section | Executive/product/policy/operations/evidence/risk section. |
| source_manifest | Danh sách nguồn và validation state. |
| underwriting_assignment | Queue, reviewer, SLA, history. |
| underwriting_review | Findings/annotations. |
| underwriting_information_request | Yêu cầu bổ sung có cấu trúc. |
| underwriting_decision | Outcome, reasons, conditions, validity, sources. |
| decision_condition | Condition lifecycle và evidence closure. |
| submission_diff | Khác biệt giữa versions. |
| review_access_event | Audit truy cập nguồn nhạy cảm. |
| Agent | Nguồn retrieval | Không được tự suy đoán |
| --- | --- | --- |
| Product Agent | Product catalog, customer facts, need profile, product evidence, approved commercial rules. | Phí, lãi suất, limit, approval hoặc điều kiện không có nguồn. |
| Legal/Policy Agent | Policy/rule registry, KYC/UBO evidence, legal docs, exception records. | Kết luận pháp lý không policy; tự gỡ absolute block; tự suy ra UBO. |
| Operations Agent | SOP, process catalog, implementation checklist, integration/signature policy. | Cam kết SLA/chức năng không SOP; tự đánh dấu ready. |
| Requirement Compiler | Structured outputs của 3 Agent, requirement/policy registry, evidence inventory. | Tạo checklist tự do không requirement code. |
| Underwriting Compiler | Frozen submission snapshot, evidence matrix, source manifest, validated outputs. | Tự thêm claim, che conflict hoặc sửa số liệu. |
| Tier | Nguồn | Policy sử dụng |
| --- | --- | --- |
| Tier 1 | Core/CRM versioned data, approved catalog, policy registry, verified/signed documents. | Ưu tiên cao; kiểm tra freshness/applicability. |
| Tier 2 | Verified Evidence, specialist review, approved exception, SOP. | Dùng trong đúng scope. |
| Tier 3 | Customer upload pending, unverified form, meeting note. | Unverified fact; không tạo kết luận chắc chắn. |
| Tier 4 | Model inference từ facts. | Gắn INFERENCE, confidence và supporting refs. |
| Tier 5 | Không có nguồn. | Không xuất như fact; tạo question/requirement hoặc abstain. |
| Lớp | Kiểm soát | Fail behavior |
| --- | --- | --- |
| Input | Auth, role, customer scope, injection, PII, file safety. | Reject/redact/quarantine. |
| Retrieval | Source allowlist, version/freshness, tenant filter, conflict. | Insufficient/retrieval error; không che thành no-match. |
| Context | Delimiter, instruction hierarchy, bỏ instruction trong document. | Flag injection; human review. |
| Schema | Pydantic/JSON schema, enum, required refs. | Reject output; retry giới hạn. |
| Claim/Evidence | Claim phải có source; quote/page/version tồn tại. | Invalidate/downgrade/block. |
| Domain | Giới hạn authority từng Agent. | Conditional/unsupported/review. |
| Risk | Absolute blocker, authenticity high-risk, conflict. | Fail-closed. |
| Action | Approval hash, version, SoD, idempotency, allowed tool. | 403/409/422; không side effect. |
| Output | Không lộ dữ liệu, calibrated wording, citations. | Redact/rewrite/block. |
| Monitoring | Drift, source outage, fallback, safety metrics. | Degrade safely và alert. |
| Ngôn ngữ an toàn
Không dùng “chắc chắn”, “đã được phê duyệt”, “đủ điều kiện” hoặc cam kết phí/limit/thời gian nếu authority/source không cho phép. Thiếu dữ liệu phải ghi rõ điều kiện và bước xác minh. |
| --- |
| Agent/Module | Metric chính | Failure nghiêm trọng |
| --- | --- | --- |
| Product Agent | Product precision/recall, bundle completeness, need-fit, evidence coverage, unsupported claim rate. | Bịa sản phẩm/giá/limit; bỏ sót; recommendation không nguồn. |
| Legal/Policy Agent | Rule accuracy, missing-info recall, blocker recall, false-clear rate, citation validity. | Gỡ block tuyệt đối; bỏ KYC/UBO; policy sai version. |
| Operations Agent | Process completeness, dependency accuracy, checklist recall, readiness accuracy. | Bỏ bước bắt buộc; tự đánh dấu ready; action sai thứ tự. |
| Requirement Compiler | Requirement precision/recall, dedup, mapping/reuse accuracy. | Yêu cầu lại hồ sơ hợp lệ; bỏ requirement bắt buộc. |
| Document Assurance | Classification/field F1, completeness/conflict recall, authenticity/signature accuracy. | Auto-verify tài liệu giả/sai; mất provenance. |
| Underwriting Compiler | Section completeness, source coverage, summary faithfulness, contradiction/diff accuracy. | Tóm tắt sai, che conflict, thêm claim không có trong snapshot. |
| Planner/Router | Routing accuracy, false-simple rate, dependency ordering. | Bỏ Agent bắt buộc. |
| Approval/Action | Authorization, idempotency, version conflict, lineage. | Execute thiếu decision/approval; duplicate side effect. |
| Hard gate pilot | Yêu cầu |
| --- | --- |
| Invalid evidence accepted | 0 |
| Non-overridable blocker cleared | 0 |
| Action without valid decision/approval | 0 |
| Critical claim citation validity | 100% hoặc claim bị block/insufficient |
| Cross-customer leakage | 0 |
| Prompt injection bypass | 0 trên adversarial suite |
| Underwriting unsupported critical claim | 0 |
| Critical route false-simple | 0 |
| Duplicate side effect | 0 |
| Bảng | Mục đích |
| --- | --- |
| underwriting_submissions | Logical submission và current state/version. |
| underwriting_submission_versions | Immutable package, hash và pinned refs. |
| underwriting_submission_sections | Typed sections và display summaries. |
| underwriting_submission_evidence_links | Claim/requirement/evidence/source mapping. |
| underwriting_assignments | Queue, reviewer, SLA, history. |
| underwriting_reviews | Findings append-only. |
| underwriting_information_requests | Structured request quay lại RM/customer. |
| underwriting_decisions | Outcome, reasons, conditions, validity, hash. |
| underwriting_decision_conditions | Condition lifecycle và evidence closure. |
| underwriting_access_logs | Audit nguồn nhạy cảm. |
| agent_evaluation_runs | Dataset/model/source versions/metrics/failures. |
| guardrail_events | Blocked stage, reason, actor, trace. |
| metadata_objects/versions/relations/events | Unified metadata plane. |
| Prompt intent tổng thể
Giữ nguyên flow bán hàng, existing/new customer handling, Evidence Requirement Compiler, Document Assurance và RM Workspace. Bổ sung Submission Readiness: khi requirement bắt buộc đã đạt, RM xem Submission Preview và duyệt đúng package hash/exact versions để gửi thẩm định. Hệ thống freeze Underwriting Submission bất biến, tạo Executive/Product/Policy/Operations views, Evidence Matrix, Source Manifest, Lineage và Diff. Mọi kết luận truy xuất được về requirement, evidence, document, page/region/span, version, validation, freshness, authenticity, signature, Agent run và policy/rule version. Underwriter tạo structured information request; evidence mới tạo snapshot/submission version mới và resubmit. Decision pin đúng submission version, có reasons/conditions/validity/source refs và không tự execute. Mọi Agent dùng Controlled Retrieval Plane, Grounding Pack, structured output, claim/evidence validator, domain/risk/action guardrails và human review. Thiếu nguồn phải abstain hoặc tạo requirement. Đánh giá riêng Product, Legal/Policy, Operations, Requirement Compiler, Document Assurance, Planner/Router và Underwriting Compiler; có hard safety gates. Toàn bộ dữ liệu dùng Unified Metadata Plane giống DeepStream: ID/type/version, relations, processor metadata, source refs, hashes, access control, audit và khả năng query/intervene/replay tại từng checkpoint. |
| --- |