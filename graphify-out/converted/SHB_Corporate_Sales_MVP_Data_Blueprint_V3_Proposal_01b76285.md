<!-- converted from SHB_Corporate_Sales_MVP_Data_Blueprint_V3_Proposal.docx -->

SHB CORPORATE SALES
EXPERT WORKSPACE
MVP bán hàng doanh nghiệp và Data Blueprint
cho hệ thống Context-Aware Expert Workspace
Hiểu bối cảnh → hiểu đúng ý định → tìm giải pháp → kiểm tra điều kiện
→ chuẩn bị case/task → RM phê duyệt → thực thi có kiểm soát
Bản đề xuất V3 • 17/07/2026
Trọng tâm: vertical slice có thể demo ngày 18/07/2026
Tác giả: Đào Quang Thắng
MVP/Hackathon Proposal – Không phải tài liệu chính sách chính thức của SHB

# TÓM TẮT ĐIỀU HÀNH
SHB Corporate Expert Workspace là một không gian làm việc nội bộ đóng vai trò như “đội chuyên gia số” đứng sau mỗi RM. Hệ thống không chỉ trả lời câu hỏi, mà hiểu RM đang làm gì, đang phục vụ doanh nghiệp nào, case đang ở bước nào và dữ liệu nào đã tồn tại; từ đó hệ thống có thể tìm giải pháp, kiểm tra điều kiện, chuẩn bị checklist/case/task và soạn phản hồi mà không buộc nhân viên nhập lại cùng một thông tin qua nhiều vòng.
Bản V3 thu hẹp câu chuyện vào một vertical slice bán hàng doanh nghiệp có thể chạy và trình diễn ngày 18/07/2026: một doanh nghiệp 500 nhân sự, nhiều nhà cung cấp, dòng tiền phân tán và cần bổ sung vốn ngắn hạn. Hệ thống phải hiểu đồng thời bốn nhu cầu — chi lương, thanh toán nhà cung cấp, quản lý dòng tiền và vốn lưu động — rồi tạo một bundle giải pháp. Nhánh giao dịch được tiếp tục chuẩn bị; riêng nhánh tín dụng dừng ở pending_information nếu thiếu UBO hoặc báo cáo tài chính.
Product, Legal/Compliance, Operations, Evidence và Approval vẫn là các vai trò chuyên môn rõ ràng nhưng cùng đọc một case state có schema. Planner chỉ lập dependency và điều phối. Những quyết định rủi ro cao thuộc về rule deterministic và con người. Mọi thao tác tạo dữ liệu thật hoặc gửi ra ngoài phải qua evidence validation, RM review và approval gắn với đúng payload.
Thông điệp cốt lõi
RM không thiếu dữ liệu; RM cần một cơ chế phối hợp tri thức liên phòng ban để biến dữ liệu thành quyết định và hành động có kiểm soát. Hệ thống tối ưu phải hiểu context trước khi đọc câu lệnh, tái sử dụng trước khi tạo mới và chỉ hỏi khi thiếu dữ liệu thực sự làm thay đổi quyết định.
Scope freeze cho MVP ngày mai
Không xây PDF ingestion, vector database persistent, CRM thật, email thật hoặc autonomous multi-agent trong sprint này. Dùng catalog/policy/SOP synthetic có version, deterministic rules, FastAPI và UI hiện có. Ưu tiên một hành trình hoàn chỉnh, dễ hiểu và có bằng chứng hơn số lượng tính năng.
## Mục tiêu kinh doanh
- Rút ngắn thời gian từ lúc tiếp nhận nhu cầu đến khi có phương án tư vấn và checklist hành động.
- Giảm trao đổi lặp giữa RM với Product, Legal/Compliance và Operations cho các câu hỏi chuẩn hóa.
- Giảm câu hỏi làm rõ không cần thiết bằng cách dùng context đã có trong workspace, CRM, DMS, task và lịch sử case.
- Đảm bảo sản phẩm, điều kiện và phản hồi quan trọng đều có nguồn, phiên bản và trạng thái hiệu lực.
- Ngăn tạo trùng case/task, ngăn gửi sai nội dung và giữ đầy đủ audit trail.
## Hai chỉ tiêu không được thỏa hiệp

## Phạm vi và giả định
- Người dùng trực tiếp là RM hoặc nhân viên kinh doanh khách hàng doanh nghiệp; khách hàng doanh nghiệp không trực tiếp tương tác với agent trong MVP.
- Dữ liệu sản phẩm, chính sách và quy trình thuộc nội bộ; MVP/hackathon dùng dữ liệu synthetic, không được coi là chính sách thật của SHB.
- Hệ thống không tự phê duyệt tín dụng, không tự chấp thuận khách hàng và không thay thế người có thẩm quyền.
- CRM/DMS/task/email được mô phỏng bằng adapter; tích hợp thật chỉ được thực hiện sau khi chốt API, IAM, retention và approval matrix.
- Tài liệu tải lên là dữ liệu không tin cậy; nội dung tài liệu không được phép thay đổi system policy hoặc quyền gọi tool.
# CẤU TRÚC TÀI LIỆU


# 1. BỐI CẢNH, ĐỐI TƯỢNG SỬ DỤNG VÀ PAIN POINT
## 1.1. Ba lớp đối tượng cần phân biệt
Giải pháp phục vụ một chuỗi giá trị gồm khách hàng doanh nghiệp, RM/nhân viên SHB và các đơn vị chuyên môn nội bộ. Việc phân biệt ba lớp này rất quan trọng: khách hàng nêu nhu cầu và cung cấp hồ sơ; RM chịu trách nhiệm quan hệ, phán đoán và phê duyệt nội dung; hệ thống AI chỉ hỗ trợ tổng hợp, đề xuất và chuẩn bị hành động.

Bảng 1. Đối tượng, vai trò và nhu cầu trong sản phẩm.
## 1.2. Câu chuyện công việc hiện tại
Một khách hàng doanh nghiệp hiếm khi chỉ hỏi về một sản phẩm. Khi doanh nghiệp nói “chúng tôi muốn trả lương, thu tiền từ đại lý, quản lý dòng tiền và có hạn mức khi thiếu hụt”, RM phải đồng thời hiểu mô hình vận hành, tra cứu nhiều dòng sản phẩm, kiểm tra hồ sơ pháp lý, xác định điều kiện tín dụng, lập danh sách hồ sơ và phối hợp các bộ phận để tạo task. Mỗi bước thường nằm ở một tài liệu, một hệ thống hoặc một đầu mối khác nhau.
- RM thu thập thông tin doanh nghiệp và diễn giải nhu cầu từ ngôn ngữ tự nhiên.
- RM tra cứu catalog, biểu phí, chính sách hoặc liên hệ Product để tạo bộ giải pháp.
- Legal/Compliance kiểm tra đăng ký doanh nghiệp, người đại diện, UBO/KYC, hiệu lực và ngoại lệ.
- Operations kiểm tra checklist, SOP, chủ sở hữu công việc, SLA và trạng thái xử lý.
- RM tổng hợp kết quả, hỏi bổ sung, tạo case/task, soạn phản hồi và theo dõi tiến độ.
Vấn đề không chỉ là thời gian tra cứu. Khi context bị thất lạc giữa các kênh, nhân viên phải nhắc lại khách hàng nào, case nào, đã có hồ sơ gì và đã hỏi gì. Công việc lặp lại phát sinh cả ở phía RM lẫn các bộ phận hỗ trợ; trong khi đó một chatbot hoặc RAG đơn chỉ trả lời được một câu hỏi nhưng không quản lý dependency, trạng thái và hành động tiếp theo.

Bảng 2. Hệ quả của quy trình phân mảnh.
## 1.3. Root causes
- Tri thức sản phẩm, pháp lý và vận hành phân tán, có phiên bản và thời hạn hiệu lực khác nhau.
- Không có shared case state thống nhất để ghi intent, facts, evidence, task, approval và lịch sử thay đổi.
- Ứng dụng chưa truyền đầy đủ workspace context sang trợ lý nên AI nhìn thấy câu lệnh nhưng không biết RM đang đứng ở đâu.
- LLM thường được kỳ vọng tự suy luận cả nghiệp vụ cứng, làm tăng rủi ro hallucination và khó audit.
- Thiếu cơ chế dedup, impact graph và partial resume nên cùng một kết quả bị tính lại hoặc cùng một task bị tạo lại.
# 2. ĐỊNH VỊ SẢN PHẨM VÀ JOB-TO-BE-DONE
## 2.1. Định vị
SHB Corporate Expert Workspace
Một workspace nội bộ giúp RM hiểu và xử lý yêu cầu khách hàng doanh nghiệp theo một case thống nhất. Hệ thống đóng vai trò đội chuyên gia số: Product tìm bộ giải pháp, Legal/Compliance kiểm tra điều kiện, Operations chuẩn bị hành động; Planner điều phối, Evidence Validator kiểm căn cứ và RM giữ quyền quyết định cuối.
Định vị này khác chatbot hỏi–đáp. Sản phẩm phải tạo được một outcome nghiệp vụ có thể kiểm chứng: RM thấy hệ thống đang hiểu gì, sản phẩm nào được đề xuất, điều kiện nào đã đạt/chưa đạt, dữ liệu nào còn thiếu, task nào đã tồn tại và payload nào sẽ được tạo nếu phê duyệt.
## 2.2. Job-to-be-done
Khi RM đang xử lý một doanh nghiệp, hệ thống phải tự nhận biết context hiện tại, hiểu yêu cầu ngắn hoặc mơ hồ, tái sử dụng dữ liệu và kết quả đã có, sau đó chuẩn bị bước tiếp theo mà không tạo công việc trùng. Công thức sản phẩm là:
Nắm bắt context nhân viên
→ hiểu intent và tự điền dữ liệu có sẵn
→ tìm sản phẩm có nguồn
→ kiểm tra điều kiện bằng rule + evidence
→ chuẩn bị/update checklist, case, task và phản hồi
→ RM xem, sửa và phê duyệt
→ executor thực thi đúng payload một lần
## 2.3. Phạm vi không làm
- Không trực tiếp thay RM cam kết với khách hàng.
- Không tự quyết định hoặc phê duyệt tín dụng.
- Không suy đoán customer ID, product ID, người nhận, phí, hạn mức hoặc điều kiện khi không có nguồn.
- Không lưu suy luận nhạy cảm về tính cách hay hiệu suất nhân viên chỉ vì có behavioral context.
- Không để agent gọi trực tiếp CRM/email; mọi write đi qua Tool Gateway, Approval Service và Action Executor.
- Không bắt đầu bằng autonomous multi-agent chạy vòng lặp mở; workflow có trạng thái và điều kiện dừng là mặc định.
# 3. CÂU CHUYỆN END-TO-END: CÔNG TY ABC
## 3.1. Tình huống
Case minh họa
Công ty ABC là doanh nghiệp sản xuất có 500 nhân viên, nhiều nhà cung cấp và dòng tiền phân tán. Khách hàng muốn SHB tư vấn chi lương, thu/chi hộ, quản lý dòng tiền và vốn lưu động. Hồ sơ hiện có gồm đăng ký doanh nghiệp và CCCD người đại diện; thông tin UBO và báo cáo tài chính gần nhất chưa có.
RM đang mở đúng customer/case trên Workspace và nhập: “Khách muốn chi lương, gom dòng tiền và có hạn mức khi thiếu hụt. Kiểm tra giúp tôi và soạn phản hồi hồ sơ còn thiếu.” Đây là một yêu cầu multi-intent: vừa tìm sản phẩm, vừa kiểm tra điều kiện, vừa chuẩn bị operations output.
## 3.2. Hệ thống phải xử lý như thế nào
- Context Engine lấy employee ID, quyền, customer/case đang chọn, tài liệu hiện có và task đang mở; không hỏi lại “khách hàng nào?”.
- Intent Resolver tách Payroll, Cash Management, Working Capital, kiểm tra eligibility và soạn phản hồi; mỗi slot có source và confidence.
- Product RAG tìm sản phẩm trong catalog kiểm soát, lọc phiên bản còn hiệu lực và trả citation.
- Eligibility Engine chạy rule UBO/BCTC; Legal RAG chỉ cung cấp căn cứ và giải thích, không tự phê duyệt.
- Planner giữ các nhánh transaction services tiếp tục, chỉ chặn nhánh tín dụng ở pending_information.
- Operations hợp nhất checklist, phát hiện task UBO đã tồn tại hay chưa, cập nhật draft thay vì tạo trùng.
- Evidence Validator chặn claim “đủ điều kiện hoàn toàn”; RM thấy lý do và nguồn.
- RM duyệt payload. Executor tạo đúng case/task một lần với idempotency key và ghi audit.

Bảng 3. Luồng demo end-to-end trong đề xuất ban đầu, được giữ lại và đặt trong kiến trúc V2.
“Wow moment” cần chứng minh
Product tìm được bộ giải pháp nhưng Legal phát hiện thiếu UBO; Planner tự thay đổi kế hoạch, giữ nhánh an toàn tiếp tục và Operations chuẩn bị đúng action bổ sung. Đây là collaboration làm thay đổi workflow, không phải ba chatbot trả lời nối tiếp.
## 3.3. Resume sau khi có UBO
Khi RM hoặc khách hàng tải lên tài liệu UBO, hệ thống không chạy lại toàn bộ case. DMS phát event, workflow tính impact từ loại tài liệu và chỉ chạy lại Eligibility → Evidence → Operations. Intent và Product được giữ nguyên nếu input hash, catalog version và mục tiêu không đổi. Checklist/email/task cũ được cập nhật theo version; approval cũ bị vô hiệu nếu payload thay đổi.
# 4. CONTEXT-AWARE: HIỂU NHÂN VIÊN ĐANG LÀM GÌ
## 4.1. Vì sao context phải đứng trước prompt
Một câu như “Kiểm tra còn thiếu gì” không đủ nghĩa nếu tách khỏi màn hình và case. Nhưng nếu RM đang ở customer COMP-ABC, case Working Capital Review, tab Financial Documents và task Kiểm tra BCTC, intent gần như đã rõ. Hệ thống phải tải context trước khi gọi LLM; LLM nhận một snapshot đã chuẩn hóa và tối thiểu hóa, không nhận dump toàn bộ CRM.
## 4.2. Tám lớp context


Bảng 4. Dữ liệu nhân viên và nguồn đề xuất.
## 4.3. Trình tự thu thập và ranh giới quyền
Authenticated employee
→ load IAM scope
→ read workspace selection
→ validate access to selected customer/case
→ load CRM/task/document metadata in parallel
→ load confirmed conversation facts
→ normalize + timestamp + provenance
→ detect conflicts and minimize context
→ return ContextSnapshot
Nếu customer đang chọn không thuộc scope, hệ thống phải fail closed với lỗi truy cập; tuyệt đối không fallback sang customer gần nhất. Permission/IAM luôn thắng user input. Context đưa vào model chỉ gồm các field cần cho intent hiện tại; không gửi toàn bộ danh sách khách hàng, email, giấy tờ định danh hoặc nội dung case khác.
## 4.4. Quy tắc ưu tiên và xung đột
- Giá trị user nêu rõ trong message hiện tại và hợp lệ.
- Workspace selection hiện tại.
- CRM/DMS/workflow còn fresh.
- Conversation fact đã được xác nhận.
- Cache còn TTL.
- LLM inference – chỉ cho field rủi ro thấp và không được ghi đè giá trị hệ thống/xác nhận.
Xung đột high-impact như customer, case, recipient hoặc product gắn external action phải được hiển thị và xác nhận trước write. Mọi field auto-fill phải có value, source, confidence, freshness và confirmed flag để UI giải thích được “AI lấy thông tin này từ đâu”.
# 5. INTENT UNDERSTANDING: HIỂU ĐÚNG VIỆC RM MUỐN LÀM
## 5.1. Intent không chỉ là một label
IntentResult phải biểu diễn job-to-be-done, sub-intents, target entities, action yêu cầu, constraints, success criteria, outputs, missing slots, ambiguity, evidence spans và field-level confidence. LLM chỉ làm semantic extraction; entity resolver, permission, ID normalization và workflow dependency là code/tool deterministic.

## 5.2. Pipeline extraction
Normalize Vietnamese text/abbreviations
→ taxonomy + minimized ContextSnapshot
→ LLM structured output
→ JSON schema validation
→ deterministic entity normalization
→ merge slots from context/tools
→ ambiguity/conflict calculation
→ confidence and clarification policy
- Không tự tạo customer, product, amount, date hoặc urgency.
- Tách nhiều intent khi một câu chứa nhiều mục tiêu.
- Giữ nguyên số tiền, ngày, tên thực thể và evidence span từ message.
- Không biết thì để null/missing; product alias chỉ trở thành product ID khi catalog resolver chứng minh.
- Không lưu chain-of-thought; chỉ lưu rationale ngắn, evidence span và decision code phục vụ audit.
## 5.3. Ví dụ output đã resolve
{
  "primary_intent": "check_missing_documents",
  "sub_intents": ["prepare_customer_response"],
  "target_customer_id": {"value":"COMP-ABC","source":"workspace","confidence":1.0},
  "active_case_id": {"value":"CASE-001","source":"workspace","confidence":1.0},
  "required_outputs": ["missing_document_checklist","customer_email_draft"],
  "unresolved_slots": [],
  "recommended_action": "continue_workflow"
}
# 6. SLOT AUTO-FILL, CONFIDENCE VÀ CHIẾN LƯỢC KHÔNG HỎI LẶP
## 6.1. Resolution order
user_explicit → workspace → workflow/case state → CRM/DMS
→ conversation_confirmed → valid cache → deterministic derivation
→ low-risk LLM inference → unresolved
Hệ thống không đặt mục tiêu tuyệt đối “không bao giờ hỏi”. Mục tiêu đúng là không hỏi lại dữ liệu có thể lấy được, không hỏi field chưa cần cho bước hiện tại và chỉ hỏi một câu có information gain cao nhất khi thiếu dữ liệu quyết định. Với external action, preview và explicit approval vẫn bắt buộc dù confidence cao.

Bảng 5. Trường có thể tự điền và trường không được suy đoán.
## 6.2. Required-now và required-later
Mỗi slot phải khai báo required_for_understanding, required_for_retrieval, required_for_eligibility và required_for_external_action. Ví dụ requested_amount có thể chưa cần để tìm product candidates nhưng bắt buộc ở bước tạo một số credit case. Workflow tiếp tục các bước an toàn, defer câu hỏi và chỉ dừng đúng node bị block.
## 6.3. Confidence policy


Bảng 6. Ma trận confidence/risk/action.
## 6.4. Clarification tối ưu
- Liệt kê unresolved slots có decision impact.
- Xếp hạng theo information gain × risk × downstream blocking.
- Tự gọi read tool trước; không hỏi field đã có trong hệ thống nguồn.
- Hỏi tối đa một câu mỗi lượt, ưu tiên lựa chọn cụ thể khi có 2–3 hypothesis.
- Lưu câu trả lời thành confirmed fact có provenance.
- Khi user sửa context, tạo correction event, invalidate đúng descendants và resume từ node sớm nhất bị ảnh hưởng.
# 7. CÁC JOURNEY CHÍNH VÀ TIÊU CHÍ TRẢI NGHIỆM

# 8. KIẾN TRÚC TỔNG THỂ

Hình 1. Kiến trúc context-aware workflow V2: specialized agents/modules nằm trong một orchestration có state, evidence và approval.
## 8.1. Các lớp kiến trúc

## 8.2. Vì sao không dùng autonomous multi-agent làm mặc định
Multi-agent có giá trị khi các vai trò có dữ liệu, tool, output contract và dependency khác nhau. Tuy nhiên các bước nghiệp vụ, trạng thái và điểm phê duyệt phải deterministic để retry, resume và audit. Vì vậy kiến trúc đề xuất giữ tên Product Agent, Legal Agent và Operations Agent ở tầng sản phẩm, nhưng runtime triển khai chúng như module/node typed; chỉ thêm planner reasoning ở case thực sự đa nhánh.

Bảng 7. Routing giữa yêu cầu đơn giản và phức tạp.

Bảng 8. Chức năng, input và output của các khối trong proposal gốc.
## 8.3. Shared contracts
Mọi module giao tiếp qua typed state/command, không truyền dict tùy ý. ID chuẩn gồm case_id, trace_id, employee_id, customer_id, task_id và document_id. Mọi output có schema_version; mọi field suy luận có source/confidence/confirmed; mọi evidence có source/version/location; mọi external action có payload hash và idempotency key.
new → understanding → clarification_required → planned → in_analysis
→ pending_information | pending_review | pending_approval
→ executing → completed | rejected | failed

Bảng 9. Ý nghĩa và chuyển tiếp trạng thái nghiệp vụ.
# 9. DATA STRATEGY VÀ MARKET DATA
## 9.1. Câu hỏi phải trả lời trước khi xây AI
Một solution context-aware/RAG chỉ tốt bằng dữ liệu mà nó có quyền sử dụng và có thể truy vết. Vì vậy đội dự án phải phân biệt bốn câu hỏi: dữ liệu có tồn tại không; có lấy được bằng kênh ổn định không; có quyền dùng cho mục đích AI không; và dữ liệu có đủ fresh/complete/provenance để ảnh hưởng quyết định không. “Có thể tìm thấy trên web” không đồng nghĩa “khả dụng cho production”.
- Dữ liệu nào là nguồn sự thật nội bộ bắt buộc và không thể mua ngoài?
- Dữ liệu official/open/commercial nào có thể xác minh hoặc làm giàu?
- Source nào được phép ảnh hưởng product matching, eligibility hoặc chỉ hiển thị tham khảo?
- Join key nào nối được external entity với customer_id mà không merge nhầm?
- Owner, legal basis/license, retention, data residency, update SLA và exit plan là gì?
- Pipeline nào biến raw source thành Gold artifact có version, ACL, quality và lineage?
## 9.2. Phân tầng nguồn và quyền quyết định

Hard veto
Source thiếu owner, legal basis/license, purpose, access method hợp lệ hoặc provenance không được publish vào serving layer dù tổng điểm chất lượng cao.
## 9.3. Bản đồ dữ liệu cần cho solution

## 9.4. Market data landscape hiện có (khảo sát 17/07/2026)
Các nguồn dưới đây phù hợp để shortlist/POC. Availability được ghi nhận từ trang chính thức hoặc trang sản phẩm tại thời điểm khảo sát; trước tích hợp phải xác minh API, quota, giá, license, data processing terms và coverage bằng mẫu thực tế.

Những nguồn bên ngoài trên không thay thế dữ liệu nội bộ. Product name/fee/limit/policy/SOP của SHB phải đến từ data owner SHB. CIC/KYC/vendor response không được lưu hoặc đưa vào prompt ngoài phạm vi được phép; việc vendor cung cấp một score không cho phép LLM tự động phê duyệt hoặc từ chối khách hàng.
## 9.5. Data fitness score và quy trình chọn source/vendor

- Chọn 100–500 synthetic/de-identified entities đại diện segment và xác định ground truth mẫu.
- Đo coverage, field completeness, match precision/recall, stale rate, latency và cost.
- Red-team tên Việt Nam có dấu/không dấu, viết tắt, tên gần giống và thay đổi địa chỉ.
- Kiểm điều khoản cho caching, embeddings, derived scores, retention, subprocessors và deletion evidence.
- Chạy shadow mode; SME/Compliance ký Data Source Acceptance Record trước khi source ảnh hưởng quyết định.
## 9.6. Data Source Card và inventory bắt buộc
Mỗi source có một Source Card versioned gồm source_id/domain/tier, business owner/data steward/technical owner, purpose và prohibited uses, decision role, legal basis/license/DPA, sensitivity, residency/retention, access/auth/quota/SLA, schema/format, identifiers/join keys, freshness/stale behavior, quality gates, ingestion lineage, consumers và lifecycle status. Đây là contract để AI coding không tự kết nối một nguồn chỉ vì thấy URL hoặc file.
## 9.7. Data preparation pipeline
Discover/Register source
→ owner + legal/license/privacy assessment
→ acquire raw to quarantine + manifest/hash
→ malware/type/schema validation
→ parse/OCR/table extraction
→ normalize encoding, units, dates, identifiers
→ entity resolution to internal canonical IDs
→ quality profiling + source reconciliation
→ PII classification/minimization/masking + ACL
→ version/effective/change detection
→ publish Silver normalized data
→ publish Gold product/rule/context/eval artifacts
→ chunk/index or compile rules
→ acceptance tests + owner sign-off
→ Serving with lineage, trace and monitoring


## 9.8. Cách xử lý theo loại dữ liệu

## 9.9. Entity resolution và quality gates
customer_id nội bộ là canonical ID. Business registration/tax ID, LEI và vendor ID là external identifiers có source/version. Exact stable-ID match được ưu tiên; fuzzy name/address chỉ tạo candidate. High-impact merge hoặc switch phải được xác nhận. Tuyệt đối không join hai doanh nghiệp chỉ bằng tên viết tắt.

## 9.10. MVP data pack và Definition of Done
- 10 synthetic companies thuộc 4–5 segment/industry, stable IDs và permission scopes.
- 8–12 products; 20–30 product/legal/SOP documents có version/effective dates, gồm superseded/conflict cases.
- 5–10 blocking/warning/missing rules có source mapping.
- 50 intent conversations có workspace context, abbreviations, corrections và multi-intent.
- 40 RAG queries; 40 eligibility cases; 40 E2E; 25 security; 20 reliability scenarios.
- Một official/vendor adapter POC ở shadow mode; không bắt buộc cho offline MVP.
Data Definition of Done: 100% source phục vụ có valid Source Card, owner/purpose/lineage/version; mọi Product/Legal important claim trace được Gold → Silver → raw/official source; unauthorized/unlicensed source exposure = 0; stale policy used for time-sensitive decision = 0; high-risk entity merge false positive = 0; ingest report tái lập được.
## 9.11. Nguồn tham khảo cho market scan

Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 có hiệu lực từ 01/01/2026; Legal/Privacy phải thẩm định cụ thể từng source và flow. Dữ liệu public không mặc nhiên được tự do ingest/reuse; PEP/adverse media và hồ sơ khách hàng cần purpose, access, review, retention và false-positive remediation rõ ràng.
## 9.12. Vertical slice dữ liệu cho case bán hàng doanh nghiệp
MVP không bắt đầu từ catalog sản phẩm. Nó bắt đầu từ một câu chuyện bán hàng có đủ dữ liệu để mọi module cùng làm việc: RM đang mở hồ sơ Công ty ABC, biết doanh nghiệp có 500 nhân sự, nhiều nhà cung cấp và dòng tiền phân tán; khách hàng nói ngắn gọn rằng muốn trả lương, trả nhà cung cấp và cần vốn cho mùa cao điểm. Context Engine bổ sung dữ liệu đã có, Intent Engine chuẩn hóa nhu cầu, Product tạo bundle, Legal kiểm tra điều kiện, Operations chuẩn bị checklist và Evidence kiểm tra mọi claim trước khi RM duyệt.

Luật nhất quán dữ liệu
Mọi record phát sinh từ case này phải dùng cùng canonical IDs. Product không được đổi customer segment; Legal không tự tạo hồ sơ chưa có; Operations không được coi nhánh tín dụng đã sẵn sàng; Evidence không được trích một policy khác version. Nếu một agent thiếu dữ liệu, nó ghi missing field vào shared state thay vì tự bịa.
## 9.13. Form F-01 — RM Workspace và context nhân viên
Form này được hệ thống tự lắp từ SSO/IAM, màn hình đang mở, CRM và lịch sử case. RM chỉ sửa khi phát hiện sai; không phải nhập lại mỗi lần. Mỗi field lưu value, source, observed_at, confidence và confirmed.

## 9.14. Form F-02 — Sales discovery cho khách hàng doanh nghiệp
Đây là form nghiệp vụ quan trọng nhất cho Intent và Product matching. Form phải hỗ trợ ba trạng thái: known (đã có), inferred (suy luận có provenance) và unknown (chưa biết). Unknown không đồng nghĩa phải hỏi ngay; chỉ hỏi nếu field đó chặn quyết định hiện tại.

{
  "case_id": "CORP-DEMO-001",
  "company": {"customer_id": "COMP-ABC", "employees_count": 500, "annual_revenue_vnd": 120000000000},
  "sales_signals": {"supplier_payments_per_month": 1200, "cash_flow": "distributed", "erp": "file_export"},
  "funding_need": {"amount_vnd": 20000000000, "tenor_months": 6, "purpose": "seasonal_working_capital"},
  "unknown_fields": ["pay_day", "approval_matrix", "api_readiness"]
}
## 9.15. Form F-03 đến F-08 — Contract dữ liệu cho từng agent
Các form dưới đây không phải prompt riêng lẻ. Đây là hợp đồng dữ liệu giữa các module. Mỗi output có schema_version, case_id, generated_at, provenance và validation_status; chỉ shared state là nơi hợp nhất trạng thái cuối.

## 9.16. Mẫu dữ liệu chi tiết cho Product, Legal và Operations
### Product Catalog record
{
  "product_id": "SYNTH-PROD-BULK-PAYMENT", "product_name": "Chi hộ nhà cung cấp",
  "category": "payments", "target_segments": ["SME", "large_corporate"],
  "supported_needs": ["supplier_payment"], "features": ["file_payment", "multi_level_approval"],
  "prerequisites": ["corporate_payment_account"], "required_documents": ["service_agreement", "business_registration"],
  "compatible_products": ["SYNTH-PROD-CASH-MGMT"], "exclusion_conditions": [],
  "source_document_ids": ["SYNTH-DOC-PRODUCT-004"], "document_version": "1.0",
  "effective_date": "2026-01-01", "status": "active", "data_label": "SYNTHETIC DEMO DATA"
}
### Eligibility Rule record
{
  "rule_id": "SYNTH-RULE-WC-FS-001", "product_id": "SYNTH-PROD-WORKING-CAPITAL",
  "field": "financial_reports.has_recent", "operator": "eq", "expected": true,
  "severity": "blocking", "on_unknown": "pending_information",
  "required_evidence_types": ["financial_statement"],
  "source_document_id": "SYNTH-DOC-CREDIT-001", "source_section": "5.2",
  "version": "1.0", "effective_from": "2026-01-01", "data_label": "SYNTHETIC DEMO DATA"
}
### Operations SOP record
{
  "workflow_id": "SYNTH-SOP-CORP-SALES-001", "product_id": "SYNTH-PROD-BULK-PAYMENT",
  "step_id": "OPS-03", "sequence": 3, "precondition": "eligibility_status != failed",
  "task_template": "Xác nhận ma trận phê duyệt và định dạng file thanh toán",
  "owner_role": "RM", "sla_hours": 8, "approval_required": false,
  "dedup_key_template": "{case_id}:{product_id}:{step_id}",
  "source_document_id": "SYNTH-DOC-SOP-002", "version": "1.0"
}
## 9.17. Sinh dữ liệu synthetic hiệu quả bằng scenario graph
Cách sinh dữ liệu hiệu quả nhất cho MVP là scenario-first, constraint-driven và reproducible. Không dùng LLM để tạo tự do hàng nghìn record ngay từ đầu. Trước tiên định nghĩa archetype doanh nghiệp, nhu cầu, policy/rules và expected outcome; sau đó generator tạo các bảng liên quan bằng seed cố định. LLM chỉ hỗ trợ paraphrase câu nói của RM và tạo biến thể tài liệu; code deterministic giữ ID, số tiền, trạng thái và ground truth.
- Bước 1 — Chọn archetype: manufacturing-500-staff, retail-multi-outlet, logistics-import-export.
- Bước 2 — Gắn need graph: payroll, supplier_payment, cash_management, working_capital.
- Bước 3 — Chọn product bundle và tạo prerequisite/rule graph tương ứng.
- Bước 4 — Áp dụng missingness có chủ đích: thiếu UBO/BCTC, stale policy, conflicting representative hoặc tool timeout.
- Bước 5 — Sinh conversation variants: đủ dấu/không dấu, viết tắt, câu ngắn, correction, multi-intent và out-of-scope.
- Bước 6 — Tạo ground truth trước output model: expected intents, product IDs, blocking rules, missing docs, workflow status và allowed actions.
- Bước 7 — Validate referential integrity, schema, range, effective dates, ACL và evidence linkage.
- Bước 8 — Đóng gói manifest gồm seed, generator_version, source template hashes và expected metrics.

Phân bổ dữ liệu khuyến nghị
60% happy/near-happy path để demo ổn định; 25% missing/conflict để chứng minh hệ thống biết dừng; 15% adversarial/failure để chứng minh guardrail. Mỗi high-risk negative case phải có expected status và expected forbidden action, không chỉ expected text.
## 9.18. Form F-09 — Synthetic Scenario Specification

## 9.19. Đánh giá dữ liệu thị trường theo tính phù hợp và khả dụng
Market scan chỉ trả lời nguồn nào tồn tại và có thể thử nghiệm. Nó không tự cấp quyền sử dụng. Trước khi production ingest, từng nguồn phải qua Source Card, legal basis/license, owner, access method, data minimization, retention và quality POC. Trong MVP ngày mai, nguồn thị trường chỉ được mô phỏng hoặc dùng làm thiết kế adapter; không phụ thuộc kết nối mạng khi demo.

Nguồn chính thức được kiểm tra tại thời điểm 17/07/2026 cho thấy: Cổng đăng ký doanh nghiệp hỗ trợ tra cứu và dịch vụ thông tin; GLEIF cung cấp API và Golden Copy/delta data, trong đó Level 1 trả lời “who is who” và Level 2 hỗ trợ quan hệ sở hữu; UN và OFAC cung cấp sanctions data ở định dạng máy đọc. Những nguồn này phù hợp để verify/enrich/screen, nhưng quyết định bán sản phẩm và eligibility vẫn cần dữ liệu nội bộ, policy hiện hành và human governance.
## 9.20. Pipeline chuẩn bị và xử lý dữ liệu theo từng agent
Source registration + owner/license/purpose
→ Raw/Quarantine (immutable hash, malware/OCR/encoding checks)
→ Silver (canonical IDs, normalized units, dedup, entity resolution, ACL)
→ Gold by agent (Product catalog / Rule registry / SOP / Context views / Eval labels)
→ Serving (API, rule engine, sparse+dense index, feature/context store)
→ Trace + feedback + correction + version retirement

## 9.21. Data acceptance checklist cho MVP
- Case hero chạy offline từ create → pending_information → bổ sung UBO/BCTC → pending_approval → mock execute.
- Mọi agent output chứa đúng case_id/customer_id và validate được bằng schema; không orphan record.
- Sáu sản phẩm synthetic có ID, supported needs, prerequisites, source, version, effective date và data label.
- Nhánh transaction không bị mất chỉ vì nhánh working capital bị block.
- Mỗi blocking check chỉ ra field/document thiếu và source rule; unknown không được biến thành pass.
- Email/task chỉ là draft trước approval; approval token không cho phép payload đã bị sửa.
- Golden scenarios tái lập bằng seed; generator và dataset manifest được version hóa.
- Tất cả nguồn thị trường có availability/decision role rõ; source chưa có license không được ingest production.
# 10. PRODUCT KNOWLEDGE, INGESTION VÀ HYBRID RAG
## 10.1. Giới hạn cần khắc phục
Baseline hiện tại dùng hash embedding deterministic và catalog in-memory. Cách này phù hợp demo nhưng chưa đủ cho PDF/Word/Excel thật, versioning, ACL, hiệu lực chính sách, persistent vector index và đánh giá retrieval. V2 phải có ingestion report và index manifest; không được gọi một danh sách hard-code là production RAG.
## 10.2. Nguồn và ingestion

File/API → SHA-256 + document/version → parser/OCR router
→ text/table extraction → Unicode cleaning + quality checks
→ structure-aware chunking → metadata/ACL enrichment
→ dense embedding + sparse index → manifest + ingest report
Chunk phải giữ section path, page, product ID, effective date, active flag, access scope, content hash và parent/neighbor references. Bảng được lưu thành summary + row chunks nhưng luôn giữ header và unit; eligibility rule không tách khỏi product ID.
## 10.3. Retrieval và matching
query normalization + resolved slots
→ ACL/effective-date/segment filters
→ dense top-20 + sparse top-20
→ weighted fusion (khởi tạo 0.6/0.4, tune bằng eval)
→ rerank + dedup + source diversity
→ threshold/OOS gate → top 3–5 chunks
RAG chỉ tạo candidates. Product Matcher tính intent fit, segment fit, size/revenue fit và workflow signal; prerequisites thiếu được trừ điểm hoặc hiển thị riêng. Trường eligible phải để unknown cho tới Eligibility Engine. Không recommendation nào được phép sử dụng product name ngoài controlled catalog.
# 11. ELIGIBILITY, LEGAL VÀ COMPLIANCE
## 11.1. Nguyên tắc phân quyền quyết định
Rule deterministic sở hữu kết quả đạt/không đạt/pending cho điều kiện đã mã hóa. Legal RAG cung cấp điều khoản, phiên bản và giải thích. Live tools đọc KYC/UBO/watchlist khi được phép. LLM không được downgrade severity, không tự kết luận “đủ điều kiện” và không được bỏ qua input stale.
Permission/sanction hard block
→ legal/regulatory blocking
→ product eligibility blocking
→ missing required information
→ warning/advisory
→ LLM explanation grounded by evidence
## 11.2. Semantics kết quả

Trong case ABC, thiếu UBO và BCTC chỉ chặn nhánh Working Capital. Payroll/Cash Management không bị loại bỏ nếu điều kiện riêng của chúng thỏa. Product vẫn hiển thị “blocked/pending” cùng lý do thay vì bị xóa khỏi phương án, giúp RM hiểu trade-off và thông tin cần bổ sung.
## 11.3. Failure policy
- Rule registry không tải được: fail closed cho eligibility.
- Legal index lỗi: chỉ tiếp tục nếu rule/source cached còn hiệu lực; nếu không chuyển pending_review.
- KYC timeout: không được trả passed; chuyển pending_review/pending_information.
- Hai policy active mâu thuẫn: hiển thị cả hai nguồn, dừng để người có thẩm quyền review.
- Malformed blocking rule: quarantine + alert, không được silently ignore.
# 12. WORKFLOW ORCHESTRATION, RETRY VÀ PARTIAL RESUME
## 12.1. Node contract

## 12.2. Routing và giới hạn vòng lặp
Yêu cầu chỉ đọc, một intent, không eligibility rủi ro cao và context đủ có thể đi fast path. Multi-intent, credit/KYC, missing-information loop hoặc draft/write phải đi complex route. DAG phải kiểm unknown dependency và cycle; max adaptive loops = 3. Planner không có quyền gọi business write tool.
## 12.3. Retry và idempotency

## 12.4. Impact graph

# 13. OPERATIONS: CHECKLIST, ARTIFACT REUSE VÀ DEDUP
## 13.1. Output chỉ là draft
Operations nhận intent/context đã validate, product recommendation có evidence, eligibility result, existing case/task/artifacts và SOP version. Module tạo decision brief, checklist, customer message draft, CRM case draft và task drafts; không được tạo side effect.
## 13.2. Checklist engine
Checklist là union có giải thích của product prerequisites, legal missing documents, KYC/UBO, SOP và context-specific requirements. Dedup dùng controlled document taxonomy, không chỉ string equality. Mỗi item lưu document_type_id, status, reason, product/rule/evidence IDs và existing document reference.
## 13.3. Drafting an toàn
- Dùng template trước; LLM chỉ cải thiện văn phong từ structured verified fields.
- Không thêm phí, lãi suất, hạn mức, deadline hoặc điều kiện không có source.
- Recipient từ CRM chỉ là candidate và phải được RM verify trước send.
- RM edit tạo version/content hash mới và làm approval cũ mất hiệu lực.
- Email không cam kết phê duyệt tín dụng; nêu rõ hồ sơ cần bổ sung và mục đích liên hệ.
## 13.4. Dedup key và reuse policy
org + customer_id + case/business_request_id + task_type
+ product_id? + workflow_step + normalized_subject_hash

# 14. EVIDENCE, GUARDRAILS, APPROVAL VÀ EXECUTION
## 14.1. Defense in depth
- Authentication/session và RBAC/ABAC trước retrieval.
- File type/size/malware, prompt injection và PII minimization ở input.
- ACL/effective date filter trước khi chunk đến model.
- Schema validation và deterministic exact-match cho số, phí, limit, unit.
- Tool allowlist theo caller/module, risk, scope, approval và idempotency.
- Approval token gắn case, approver, permissions, payload hash, expiry, nonce và one-time use.
- Executor load latest state và verify lại evidence/blocking/permission trước side effect.
## 14.2. Evidence validation
Validator kiểm source identity/version/effective status, quote presence, deterministic value/unit match và semantic support. Claim không được hỗ trợ bị loại khỏi output khách hàng, đánh hallucination_flag, re-retrieve một lần và sau đó chuyển review/failure. Numeric claims không được pass chỉ bằng semantic similarity.
## 14.3. Approval integrity
verify auth/session → load latest state
→ verify signature/expiry/nonce/one-time use
→ recompute payload hash
→ verify evidence + no blocking + permissions
→ acquire idempotency lock → call adapter
→ reconcile uncertain outcome → persist audit → consume token
Nguyên tắc bất biến
AI chỉ phân tích, đề xuất và soạn nháp. Tạo case/task hoặc gửi phản hồi ra ngoài chỉ được thực hiện khi RM (hoặc cấp có thẩm quyền theo matrix) phê duyệt đúng payload. Chỉnh một ký tự trong payload sau approval cũng phải làm token cũ mất hiệu lực.
# 15. API V2 VÀ RM WORKSPACE
## 15.1. API contract

Auth principal lấy từ session/token, không tin employee_id trong body. API dùng stable error codes, trace ID, ETag/state version và Idempotency-Key cho write. Client không được tự chọn bỏ qua evidence node khi resume.
## 15.2. Các panel trong UI
- Context Header: RM/role, customer, active case, current step, product, missing info; có source/freshness tooltip.
- Intent Preview: “Hệ thống hiểu rằng…”, primary/sub-intents, resolved fields, assumptions và một clarification nếu blocking.
- Product/Evidence: candidates, score components, eligibility, source quote/version, blocked/pending reason.
- Operations: checklist, existing/reuse/update/create badge, email editor/version diff và SLA source.
- Approval: exact actions, target/recipient, payload diff, risk/evidence và approve/reject.
- Timeline: context loaded, intent resolved, retrieval/rules, draft reuse/update, approval/execution; không phơi chain-of-thought.
# 16. STORAGE, OBSERVABILITY VÀ RELIABILITY
## 16.1. Persistent storage

## 16.2. Observability tối thiểu
- Trace ID xuyên API → context → intent → workflow → retrieval/rules/tool.
- Log JSON có event code, prompt/workflow/rule/index version và sanitized IDs; không log raw PII, token hoặc email nhạy cảm.
- Metrics cho context stale/conflict/auto-fill, intent schema/clarification, RAG hit/empty/latency, eligibility pending/block, resume/dedup, approval/action và cost.
- Timeout mọi network/model call; backoff chỉ cho safe reads, circuit breaker theo dependency, DLQ cho async job và reconciliation cho write timeout.
- Cache key luôn gồm version và permission scope; không reuse cross-customer/cross-scope.
## 16.3. SLO đề xuất

# 17. EVALUATION VÀ QUALITY GATES
Không dùng một demo đẹp làm bằng chứng chất lượng. Hệ thống phải đo riêng context, intent, retrieval, eligibility, workflow, safety và end-to-end; deterministic metrics là gate chính, LLM-as-judge chỉ dùng cho clarity/tone hoặc semantic support khó xác định.



Bảng 10. Bộ metric nghiệp vụ/kỹ thuật của proposal ban đầu được giữ lại làm lớp bổ sung.
# 18. KẾ HOẠCH BUILD THỐNG NHẤT CHO AI CODING
## 18.1. Nguyên tắc contract-first
JSON schemas là source of truth cho shared state, context, intent và tool contract. Nếu code cần khác contract, thay đổi phải đi cùng migration, tests và progress log. AI coding phải đọc INDEX → PROGRESS → build protocol → contract liên quan → module plan → acceptance trước khi báo hoàn thành.
- Không thêm field hoặc status rải rác trong code.
- Không bắt đầu task khi dependency chưa Done, trừ adapter mock có interface rõ.
- Mỗi task có unit, integration, metrics/log và security considerations.
- Không gọi một module là Done chỉ vì happy path chạy; phải đạt acceptance và regression liên quan.
- Bảo toàn `/api/v1` baseline trong lúc thêm `/api/v2`, chỉ remove sau E2E và quyết định compatibility.
## 18.2. Ordered backlog

## 18.3. Vertical checkpoints
- Checkpoint 1 — Understand only: “Kiểm tra còn thiếu gì” + workspace → đúng intent/slots, không hỏi customer/case.
- Checkpoint 2 — Grounded recommendation: ABC multi-intent → products + eligibility + citations.
- Checkpoint 3 — Controlled workflow: pending information → upload UBO → partial resume → approval → một mock action.
- Checkpoint 4 — Pilot-shaped app: persistent state, correction UI, trace và eval report.
## 18.4. Lộ trình triển khai theo giai đoạn

# 19. HIỆN TRẠNG, ĐÃ CÓ VÀ CHƯA CÓ
Baseline repo hiện có là MVP FastAPI với deterministic workflow, synthetic data và demo UI. Contracts V2, Employee/Workspace Context và Context Assembler đã được triển khai; Intent V2 và các module sau chưa được nối vào runtime E2E. Tại thời điểm cập nhật, toàn bộ 73 automated tests đang pass. Vì vậy hướng an toàn cho ngày 18/07/2026 là harden vertical slice `/api/v1` đang chạy, không cố hoàn thành toàn bộ backlog V2 và không dùng từ “production-ready”.

# 20. RỦI RO, DỮ LIỆU CẦN CÓ VÀ QUYẾT ĐỊNH MỞ
## 20.1. Rủi ro chính

Bảng 11. Rủi ro và biện pháp kiểm soát.
## 20.2. Dữ liệu cần có

## 20.3. Quyết định phải chốt trước pilot
- Intent taxonomy nào phản ánh đúng công việc RM và ai là owner?
- Field nào bắt buộc ở từng workflow stage; validity window của KYC/BCTC/task result?
- Khi CRM và document mâu thuẫn, nguồn nào thắng?
- Action nào RM tự approve, action nào cần cấp khác; pending information có được gửi email sau RM approve không?
- Vector DB, embedding, model gateway và data egress policy chuẩn nội bộ?
- Tenant/branch isolation, retention, encryption, tamper-evident audit và on-call/SLO ownership?
Cách AI coding xử lý điều chưa biết
Dùng interface/mock và gắn nhãn ASSUMPTION hoặc DATA REQUIRED; không tự bịa endpoint, policy, SLA hay quyền. Mọi temporary default phải được ghi vào decision/deviation log và giữ adapter thay thế được.
# 21. KẾT LUẬN VÀ PITCH
Đề xuất V2 không thay đổi câu chuyện cốt lõi: SHB xây một đội chuyên gia AI đứng sau mỗi RM. Điểm trưởng thành của V2 là đội chuyên gia này không hoạt động như các chatbot độc lập. Họ cùng đọc một case state, làm việc theo contract, dùng đúng dữ liệu và tool, dừng đúng lúc, tái sử dụng công việc cũ và để RM giữ quyền quyết định cuối.
Khả năng tạo khác biệt lớn nhất không nằm ở việc LLM nói hay hơn, mà ở việc hệ thống hiểu context sát hơn: biết RM đang ở customer/case nào, đã làm gì, thiếu gì và bước tiếp theo là gì. Khi context được chuẩn hóa, intent chính xác hơn; khi intent có provenance và confidence, workflow ít hỏi lại hơn; khi workflow có evidence, dedup và approval, AI mới tạo được giá trị vận hành mà vẫn kiểm soát rủi ro.
Pitch chốt
Chúng tôi không xây chatbot cho khách hàng doanh nghiệp. Chúng tôi xây một Context-Aware Expert Workspace đứng sau mỗi RM: hiểu đúng công việc đang diễn ra, phối hợp Product–Legal–Operations, biến tri thức thành phương án và hành động có căn cứ, nhưng chỉ thực thi sau khi con người phê duyệt.
# PHỤ LỤC A — TOOL/API VÀ HỢP ĐỒNG TÁC VỤ

Bảng A1. Tool/API tối thiểu theo domain.
Trong V2, danh sách trên phải đi qua Tool Registry có caller allowlist, JSON schema, risk, approval_required, timeout/retry và idempotency policy. Tên tool là contract nghiệp vụ, production endpoint được triển khai bằng adapter sau khi có specification thật.
# PHỤ LỤC B — NHIỆM VỤ XÂY DỰNG CHI TIẾT CHO CÁC KHỐI

Bảng B1. Quy trình xây dựng chung cho mỗi module/agent.

Bảng B2. Planner Agent – backlog chi tiết.

Bảng B3. Product Agent – backlog chi tiết.

Bảng B4. Legal Agent – backlog chi tiết.

Bảng B5. Operations Agent – backlog chi tiết.

Bảng B6. Evidence/Guardrail/HITL – backlog chi tiết.
# PHỤ LỤC C — DỮ LIỆU CHO TỪNG AGENT/MODULE

Bảng C1. Dữ liệu dùng chung.

Bảng C2. Dữ liệu cho Planner.

Bảng C3. Dữ liệu cho Product.

Bảng C4. Dữ liệu cho Legal.

Bảng C5. Dữ liệu cho Operations.

Bảng C6. Dữ liệu cho Evidence/Guardrail.
# PHỤ LỤC D — CATALOG SẢN PHẨM DOANH NGHIỆP MINH HỌA
Lưu ý dữ liệu
Danh mục dưới đây được giữ lại từ proposal ban đầu để bảo toàn câu chuyện và độ chi tiết. Đây là taxonomy/minh họa cho thiết kế Product RAG, không xác nhận tên thương mại, điều kiện, biểu phí hay chính sách hiện hành của SHB. Trước pilot, Product/Risk phải map sang product_id, version, effective date và source chính thức.
Bảng D1. Giai đoạn phát triển của doanh nghiệp và nhóm nhu cầu.

Bảng D2. Tài khoản và tiền gửi doanh nghiệp.

Bảng D3. Ngân hàng số và quản trị giao dịch.

Bảng D4. Cash Management.

Bảng D5. Thu hộ và đối soát.

Bảng D6. Chi hộ và thanh toán.

Bảng D7. Payroll và dịch vụ nhân viên.

Bảng D8. Vốn lưu động và tín dụng ngắn hạn.

Bảng D9. Tín dụng đầu tư trung/dài hạn.

Bảng D10. Bảo lãnh.

Bảng D11. Thanh toán quốc tế và trade finance.

Bảng D12. Ngoại hối.

Bảng D13. Thẻ doanh nghiệp.

Bảng D14. Supply Chain Finance.

Bảng D15. Merchant acquiring và thanh toán bán hàng.

# PHỤ LỤC E — KẾ HOẠCH FAST-TRACK MVP TRONG 1 NGÀY
Mục tiêu của ngày build không phải hoàn thành target architecture. Mục tiêu là tạo một câu chuyện bán hàng doanh nghiệp hoàn chỉnh, ổn định và có thể giải thích. Mỗi khối thời gian kết thúc bằng một checkpoint chạy được; nếu chậm, cắt P1 trước và giữ P0.

## Thứ tự cắt scope khi thiếu thời gian
- Cắt trước: animation/UI polish, API Banking alternative, thêm customer thứ tư, LLM thật.
- Giữ bắt buộc: hero case, 6 products, branch blocking, evidence, RM approval, 10 golden cases và demo runbook.
- Không được cắt: nhãn SYNTHETIC DEMO DATA, guardrail external action, missing-information behavior và RM approval.

# PHỤ LỤC F — SYSTEM ACCEPTANCE SCENARIOS

| Chỉ tiêu | MVP | Pilot |
| --- | --- | --- |
| Unnecessary clarification rate | < 10% | < 5% |
| Unsafe external action rate | 0% | 0% |
| Duplicate task/action rate | 0% | 0% |
| Important claims with valid evidence | 100% | 100% |
| Phần | Nội dung |
| --- | --- |
| 1–3 | Bối cảnh, câu chuyện người dùng và định vị sản phẩm |
| 4–7 | Context, intent, confidence và chiến lược không hỏi lặp |
| 8–14 | Kiến trúc, chiến lược dữ liệu, Product RAG, Eligibility/Legal, Operations và Safety |
| 15–19 | API/UI, storage, observability, evaluation, lộ trình build và hiện trạng |
| 20–21 | Rủi ro, quyết định mở và kết luận |
| Phụ lục | Tool contract, state, backlog agent và catalog sản phẩm minh họa |
| Đối tượng | Vai trò trong sản phẩm | Nhu cầu chính |
| --- | --- | --- |
| SHB | Khách hàng mua, sở hữu và triển khai giải pháp | Chuẩn hóa tri thức, tăng hiệu suất RM, giảm thời gian xử lý và tăng khả năng audit |
| RM / nhân viên SHB | Người trực tiếp sử dụng hệ thống | Hiểu nhu cầu doanh nghiệp, tìm sản phẩm, kiểm tra điều kiện, tạo case/task và phản hồi khách hàng |
| Khách hàng doanh nghiệp | Đối tượng được nhân viên SHB phục vụ | Nhận phương án nhanh, đúng điều kiện, ít phải bổ sung hồ sơ và biết bước tiếp theo |
| Đối tượng | Hệ quả |
| --- | --- |
| RM | Mất thời gian tra cứu, chất lượng tư vấn phụ thuộc kinh nghiệm, khó theo dõi thông tin còn thiếu. |
| Product / Legal / Operations | Phải xử lý nhiều câu hỏi lặp lại, khó kiểm soát các phiên bản tài liệu được sử dụng. |
| SHB | Thời gian phản hồi dài, case bị chậm, khó audit và khó chuẩn hóa chất lượng phục vụ. |
| Khách hàng doanh nghiệp | Chờ lâu, phải bổ sung nhiều lần, nhận trải nghiệm không đồng nhất. |
| Bước | Khối | Hành động |
| --- | --- | --- |
| 1 | RM Workspace | RM nhập nhu cầu và tải hồ sơ. |
| 2 | Input Validator | Chuẩn hóa hồ sơ và phát hiện thiếu metadata. |
| 3 | Planner | Tạo ba task: product solution, legal eligibility, operational preparation. |
| 4 | Product Agent | Đề xuất tài khoản doanh nghiệp, payroll, thu/chi hộ, cash management và gắn điều kiện cho phần vốn lưu động. |
| 5 | Legal Agent | Xác nhận pháp nhân và người đại diện; phát hiện thiếu UBO; chưa đủ căn cứ cho phần vốn lưu động. |
| 6 | Planner | Cho phép tiếp tục phần transaction services; tạm dừng phần vốn lưu động và yêu cầu bổ sung. |
| 7 | Operations Agent | Tạo checklist, draft email và action tạo case trạng thái pending_information. |
| 8 | Evidence/Guardrail | Kiểm tra citation, chặn claim “đủ điều kiện hoàn toàn”. |
| 9 | RM Review | RM duyệt nội dung phản hồi và action. |
| 10 | Action Executor | Tạo case/task trong hệ thống mô phỏng và cập nhật dashboard. |
| Lớp | Nội dung | Nguồn | Freshness mặc định |
| --- | --- | --- | --- |
| Employee | employee_id, role, org unit | SSO/HRIS | Session / 24h |
| Permission | scopes, managed customers | IAM | 5 phút |
| Workspace | screen, selected customer/case/task/product | UI session | Realtime |
| Customer | profile, segment, KYC, products | CRM | 5 phút |
| Workflow | current node, open questions, task/artifact | State DB | Realtime |
| Documents | type, version, status, access | DMS | 5 phút |
| Conversation | goal, confirmed facts, rejected assumptions | State DB | Session |
| Preference | language, brief/email format | User settings | 30 ngày |
| Nhóm | Dữ liệu cần có | Nguồn |
| --- | --- | --- |
| Định danh | Employee ID, tên, đơn vị | SSO/HRIS |
| Vai trò | RM, Operations, Legal, Approver | IAM/RBAC |
| Phạm vi phụ trách | Chi nhánh, vùng, nhóm khách hàng | CRM/IAM |
| Danh mục khách hàng | Các doanh nghiệp RM quản lý | CRM |
| Quyền hạn | Xem, tạo, chỉnh sửa, phê duyệt | IAM |
| Chuyên môn | Sản phẩm/phân khúc thường xử lý | CRM + cấu hình |
| Ngôn ngữ | Tiếng Việt, tiếng Anh | User settings |
| Cách làm việc | Định dạng brief, email, checklist ưa thích | Preference memory |
| Công việc hiện tại | Case, task, khách hàng đang mở | Workspace |
| Công việc gần đây | Case và thao tác gần nhất | Audit/task system |
| Intent ID | Ý nghĩa | Slot chính | Rủi ro |
| --- | --- | --- | --- |
| find_product | Tìm giải pháp phù hợp | customer/profile, objective | Thấp |
| compare_products | So sánh ứng viên | product candidates | Thấp |
| check_eligibility | Kiểm tra điều kiện | customer, product | Trung bình/Cao |
| check_missing_documents | Kiểm tra hồ sơ thiếu | case/customer, workflow/product | Trung bình |
| resume_case | Tiếp tục sau cập nhật | case, changed artifact | Trung bình |
| prepare_customer_response | Soạn phản hồi | case, purpose, recipient candidate | Trung bình |
| prepare_case_task | Chuẩn bị case/task | customer/case, task type | Trung bình |
| approve_actions | Phê duyệt action | case, frozen payload | Cao |
| status_lookup / out_of_scope | Xem trạng thái / ngoài phạm vi | case/task / none | Thấp–biến đổi |
| Field | Có thể tự điền? | Cách xử lý |
| --- | --- | --- |
| Customer ID đang chọn | Có | Lấy từ workspace |
| RM ID | Có | Lấy từ SSO |
| Case ID hiện tại | Có | Lấy từ active case |
| Ngành nghề | Có | Lấy từ CRM |
| Tài liệu đã có | Có | Lấy từ document system |
| Sản phẩm đang xem | Có | Lấy từ current screen |
| Số tiền khách hàng muốn vay | Không nên suy đoán | Chỉ hỏi nếu bắt buộc |
| Người nhận email | Có điều kiện | Lấy CRM nhưng RM phải xác nhận |
| Quyết định phê duyệt | Không | Bắt buộc con người thực hiện |
| Nguồn | Base confidence | Ghi chú |
| --- | --- | --- |
| Authenticated IAM/SSO | 1.00 | Quyền vẫn phải được kiểm tra theo scope |
| Workspace selected ID | 1.00 | Có thể phát sinh conflict khi user switch |
| Fresh CRM/DMS | 0.98 | Giảm điểm nếu stale |
| User explicit current message | 0.95 | Không thể tự khai báo quyền |
| Workflow state | 0.95 | Phải cùng case/version |
| Conversation confirmed | 0.90 | Có evidence message |
| Fresh cache / deterministic derivation | 0.85 | Key gồm version và scope |
| LLM inference | ≤ 0.70 | Không dùng làm field quyết định cho write |
| Confidence | Rủi ro | Xử lý |
| --- | --- | --- |
| ≥ 0.90 | Thấp | Tự động tiếp tục |
| 0.70–0.89 | Thấp | Tiếp tục nhưng hiển thị cách hiểu |
| < 0.70 | Thấp | Hỏi một câu hoặc đưa lựa chọn |
| Cao | Cao | Hiển thị preview và yêu cầu phê duyệt |
| Thấp | Cao | Dừng, không thực hiện |
| Journey | Input | Hành vi bắt buộc |
| --- | --- | --- |
| Kiểm tra hồ sơ case đang mở | “Kiểm tra còn thiếu gì” | Tự lấy customer/case/product; trả checklist/evidence; không hỏi lại; không tạo task trùng |
| Nhu cầu đa sản phẩm | Payroll + dòng tiền + hạn mức | Tách multi-intent; block riêng credit nếu thiếu dữ liệu; giữ nhánh an toàn |
| Resume sau upload | UBO/BCTC mới | Chạy lại Legal/Evidence/Ops; giữ intent/product; update artifact |
| Sửa context | RM đổi customer/product | Hiển thị impact; invalidate descendants; không xóa audit |
| External action | RM bấm Approve | Payload diff; token hash/expiry; RBAC/evidence/idempotency; execute một lần |
| Lớp | Trách nhiệm |
| --- | --- |
| Experience | RM Workspace, Context Header, Intent Preview, Evidence, Operations, Approval, Timeline |
| API | Context, case, document, workflow, approval, search; typed contract và auth principal |
| Understanding | Context Assembler, Intent Extractor, Slot Resolver, Confidence/Clarification |
| Orchestration | Complexity Router, Planner DAG, state machine, retry, impact-based resume |
| Knowledge & Rules | Product ingestion/RAG/matcher, Legal RAG, deterministic eligibility rules |
| Operations & Safety | Checklist, draft, dedup, artifact reuse, evidence, approval, executor |
| Integration | SSO/IAM, CRM, DMS, task, email, model gateway qua adapters |
| Storage & Ops | PostgreSQL, vector DB, cache, object store, audit, traces, metrics |
| Loại yêu cầu | Ví dụ | Cách xử lý |
| --- | --- | --- |
| Tra cứu đơn giản | Phí dịch vụ, đặc điểm sản phẩm, quy trình cơ bản | Single-Agent/RAG trả lời có citation; không kích hoạt toàn bộ multi-agent. |
| Yêu cầu phức tạp | Tìm bộ giải pháp, kiểm tra điều kiện, hồ sơ và tạo bước xử lý | Planner điều phối Product, Legal và Operations Agent. |
| Ngoại lệ/rủi ro cao | Thiếu UBO, hồ sơ hết hiệu lực, điều kiện mâu thuẫn | Dừng tự động, yêu cầu bổ sung hoặc chuyển human review. |
| Khối | Chức năng | Đầu vào | Đầu ra |
| --- | --- | --- | --- |
| RM Workspace | Giao diện nội bộ để RM nhập yêu cầu, tải hồ sơ, xem agent trace, evidence, action đề xuất và phê duyệt. | Yêu cầu khách hàng, hồ sơ, ghi chú RM | Case context ban đầu |
| Input Validator & Data Normalizer | Kiểm tra file/field bắt buộc, chuẩn hóa tên doanh nghiệp, loại tài liệu, ngày hiệu lực và metadata. | PDF/DOCX/CSV/form | Dữ liệu có cấu trúc + lỗi đầu vào |
| Complexity Router | Phân loại câu hỏi tra cứu hay workflow liên phòng ban; lựa chọn single-agent hoặc multi-agent. | Intent, số domain liên quan, mức rủi ro | Route + lý do |
| Planner Agent | Phân rã mục tiêu, tạo dependency graph, giao task, theo dõi trạng thái, retry, pause và tổng hợp. | Case state, agent capability, routing/risk rules | Execution plan + trạng thái |
| Product Agent | Phân tích nhu cầu doanh nghiệp, truy xuất catalog, ghép và xếp hạng bộ giải pháp, phát hiện thông tin còn thiếu. | Company profile, needs, product KB | Recommended solution + evidence |
| Legal Agent | Kiểm tra pháp nhân, người đại diện, UBO/KYC, hiệu lực tài liệu, eligibility và ngoại lệ. | Legal docs, policies, product proposal | Eligibility status + issues + evidence |
| Operations Agent | Kiểm tra checklist, xác định bước xử lý, tạo case/task, draft email và theo dõi SLA. | Agent results, SOP, workflow rules | Case/task/report draft |
| Shared Case State | Lưu toàn bộ input, output, evidence, tool calls, status và approval trong một trạng thái dùng chung. | Kết quả từng node | State nhất quán, có thể resume |
| Tool Registry | Quản lý các tool/API mà từng agent được phép gọi; kiểm tra schema, quyền hạn và log. | Tool name, parameters, role permission | Tool result + audit event |
| Evidence Validator | Kiểm tra claim có nguồn, citation hỗ trợ đúng kết luận, tài liệu còn hiệu lực và không mâu thuẫn. | Claims + source chunks | Supported/unsupported claims |
| Risk & Guardrail Gate | Áp dụng rule bắt buộc: thiếu dữ liệu không kết luận; rủi ro cao chuyển human review; chặn action trái quyền. | Risk flags, validation result | Proceed / request info / escalate |
| RM Review & Approval | RM xem lại phương án, chỉnh sửa, phê duyệt hoặc từ chối action trước khi thực thi. | Decision brief + evidence | Approval decision |
| Action Executor | Sau phê duyệt, gọi API tạo case/task/report hoặc cập nhật trạng thái. | Approved action | Đối tượng nghiệp vụ được tạo/cập nhật |
| Audit Log + Dashboard | Hiển thị trace, tool call, task status, evidence, người phê duyệt và thời gian. | Tất cả events | Khả năng giám sát và audit |
| Trạng thái | Ý nghĩa | Chuyển tiếp hợp lệ |
| --- | --- | --- |
| new | RM vừa tạo yêu cầu | in_analysis |
| in_analysis | Agent đang xử lý | pending_information / pending_review / pending_approval |
| pending_information | Thiếu dữ liệu từ RM/khách hàng | in_analysis |
| pending_review | Có ngoại lệ hoặc rủi ro cao | pending_approval / rejected |
| pending_approval | Action đã chuẩn bị, chờ RM duyệt | executing / rejected |
| executing | Đang gọi tool tạo case/task/report | completed / failed |
| completed | Workflow hoàn tất | closed |
| failed | Tool hoặc workflow lỗi | in_analysis / manual_resolution |
| Tier | Nguồn | Ví dụ | Vai trò được phép |
| --- | --- | --- | --- |
| A – Internal authoritative | SHB sở hữu | Product master, CRM, IAM, DMS, SOP, approved policy | Nguồn chính nếu owner/version/freshness hợp lệ |
| A – Official authoritative | Cơ quan nhà nước/quốc tế | Đăng ký doanh nghiệp, VBPL, official sanction lists | Xác minh trong phạm vi/terms được phép |
| B – Licensed curated | Vendor theo hợp đồng | Business/credit data, PEP/adverse media | Enrichment/screening theo policy đã duyệt |
| C – Open/public | Open data | Macro, LEI, open company data | Discovery/benchmark; không tự pass eligibility |
| D – Derived | Do hệ thống tạo | Entity match, summary, score, embedding | Chỉ dùng kèm lineage/model/version/validation |
| E – Synthetic/labeled | Dev/eval | Demo companies, golden cases | Test/evaluation; không trộn production facts |
| Domain | Dữ liệu cần | Nguồn ưu tiên | Thị trường/ngoài SHB | Vai trò |
| --- | --- | --- | --- | --- |
| Employee/workspace | Identity, role, scope, screen/customer/case/task | SSO/IAM/HRIS/UI | Không thể mua | Context + RBAC |
| Customer/case | Master, relationship, products, interactions, tasks | CRM/DWH/task | Vendor chỉ enrich | Canonical customer_id |
| Documents | Legal/financial files, type, version, status | DMS/upload | Có OCR/parser | Extracted facts + checklist |
| Product | Catalog, ID, segment, fees/limits, prerequisites | Product master/docs | Không có nguồn ngoài đáng tin cho SHB | Product RAG/matcher |
| Legal/SOP | Policy, approval matrix, process, SLA | Legal/Compliance/Ops | Public law chỉ bổ sung | Rules + evidence |
| Business registry | Name, registration ID, address, representative, status | National registry | Public/info services | Entity verification |
| Credit | Credit history/report/score | CIC + internal credit | Controlled/licensed | Read-only risk input |
| KYC/AML | Sanctions, PEP, adverse media/watchlists | Compliance + official/vendor | Official lists + commercial feeds | Screening/review |
| Market/industry | Macro, sector, trade, benchmarks | NSO/SBV + vendor | Public/licensed | Context/benchmark |
| Eval/feedback | Intent/evidence/outcome/corrections | Synthetic + approved samples | Không có dataset đủ sát SHB | Regression and calibration |
| Nhóm | Nguồn hiện có | Dữ liệu/format | Cách dùng và giới hạn |
| --- | --- | --- | --- |
| Đăng ký doanh nghiệp Việt Nam | Cổng thông tin quốc gia về đăng ký doanh nghiệp | Tra cứu public các trường cơ bản; có information services | Verify entity; không production scrape nếu chưa có quyền/API |
| Văn bản pháp luật | CSDL quốc gia VBPL + SBV | Web/PDF, thuộc tính/hiệu lực | Legal ingestion; monitor version/effective date |
| Credit information | CIC | Credit report/information/rating products qua kênh kiểm soát | Không phải open data; chỉ adapter được cấp quyền |
| Macro Việt Nam | National Statistics Office – NSDP | GDP, CPI, trade, FX, IIP, industry/labor; Excel/SDMX | Benchmark/context; không quyết customer eligibility |
| Vietnam corporate intelligence | FiinGroup và provider tương đương | Business reports/API, risk score, industry/trade research | Commercial POC: coverage, lineage, SLA, license, calibration |
| Global legal entity | GLEIF | LEI Level 1/2, mapped IDs; free API/full/delta | Enrich entity có LEI; không thay registry Việt Nam |
| Cross-border company data | OpenCorporates/provider tương đương | Company data có source; open/commercial versioned API | Candidate resolution; verify primary source/license |
| Official sanctions/debarment | UN, OFAC, World Bank | XML/HTML/PDF/download/search | Input screening; cần matching/update/false-positive workflow |
| Curated KYC/AML | LSEG World-Check và vendor tương đương | Sanctions, PEP/RCA, adverse media, watchlists | Licensed enrichment; compliance review, PII and cross-border due diligence |
| Dimension | Trọng số | Câu hỏi kiểm tra |
| --- | --- | --- |
| Legal/license fit | 20 | Có quyền ingest, cache, derive, embed và hiển thị citation? |
| Availability/integration | 15 | API/file/event, auth, quota, sandbox, uptime? |
| Accuracy/provenance | 15 | Primary source, evidence và correction process? |
| Freshness | 15 | Update cadence phù hợp decision window? |
| Coverage | 15 | Segment/SME/Việt Nam/historical depth? |
| Joinability | 10 | Registration/tax ID, LEI hoặc stable identifier? |
| Cost/latency | 5 | Cost/case, bulk/API pricing, P95? |
| Operational fit | 5 | Monitoring, support, changelog và exit/export? |
| Layer | Nội dung | Quy tắc |
| --- | --- | --- |
| Quarantine/Raw | File/API payload bất biến + manifest/hash | Không đưa model dùng trực tiếp |
| Silver | Parsed, typed, normalized, canonical IDs, quality flags | Giữ source record và lineage |
| Gold | Approved product/policy/rules/context/eval artifacts | Owner/version/effective/ACL bắt buộc |
| Serving | API tables, vector/sparse index, rule registry, feature views | Chỉ artifact pass gate |
| Audit | Ingest report, changes, failures, source decisions | Append-only và retention controlled |
| Loại | Chuẩn bị bắt buộc |
| --- | --- |
| PDF/Word policy | SHA-256; parser/OCR; giữ heading/page/table; effective dates; structure-aware chunks; citation sample QA |
| Excel/catalog | Schema/unit/currency; product ID; effective rows; duplicate/conflict; row-level provenance |
| CRM/API | Adapter normalization; canonical ID; freshness; field-level provenance; CDC/event hoặc TTL |
| KYC/vendor response | Source record/reference; match features/score; review status; expiry; không log raw PII |
| Conversation | Message-level facts/corrections; PII redaction; retention; không lưu raw vô thời hạn |
| Task/artifact | Canonical dedup key; input/output hash; version; supersedes/reuse link |
| Eval label | Dataset version; expected IDs/outcomes/evidence; reviewer/adjudication |
| Quality dimension | Kiểm tra | Khi fail |
| --- | --- | --- |
| Completeness/validity | Required fields, type, enum, unit, effective range | Quarantine hoặc pending information |
| Uniqueness/consistency | Keys, duplicate, CRM–DMS–registry conflicts | Conflict report/pending review |
| Freshness | TTL/update/effective date | Mark stale; block time-sensitive decision |
| Provenance | Source record/location/hash/version | Không publish claim/index/rule |
| Access | ACL/customer/employee scope | Fail closed |
| Extraction quality | OCR/table/heading/citation samples | Human review hoặc loại chunk |
| Drift | Schema, coverage, value/rank distribution | Alert, canary, re-index/recalibrate |
| Nguồn | URL |
| --- | --- |
| Cổng đăng ký doanh nghiệp quốc gia | https://dangkykinhdoanh.gov.vn/vn/pages/trangchu.aspx |
| CSDL quốc gia về văn bản pháp luật | https://vbpl.vn/Pages/portal.aspx |
| CIC | https://cic.gov.vn/ |
| National Statistics Office – NSDP | https://nsdp.nso.gov.vn/ |
| FiinGroup | https://fiingroup.vn/ |
| GLEIF data/API | https://www.gleif.org/en/lei-data/access-and-use-lei-data |
| OpenCorporates API | https://api.opencorporates.com/ |
| UN sanctions | https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list |
| OFAC Sanctions List Service | https://ofac.treasury.gov/sanctions-list-service |
| World Bank Debarred Firms | https://www.worldbank.org/en/projects-operations/procurement/debarred-firms |
| LSEG Risk Intelligence | https://www.lseg.com/en/risk-intelligence |
| Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 | https://vbpl.vn/TW/Pages/ivbpq-toanvan.aspx?ItemID=179252 |
| Thuộc tính case hero | Giá trị synthetic MVP | Agent/module sử dụng |
| --- | --- | --- |
| Định danh | case_id=CORP-DEMO-001; customer_id=COMP-ABC; rm_id=RM-999 | Tất cả module, audit, approval |
| Doanh nghiệp | Công ty CP ABC Việt Nam; sản xuất hàng tiêu dùng; 500 nhân sự; doanh thu 120 tỷ VND/năm | Context, Intent, Product, Legal |
| Vận hành tiền | 6 tài khoản tại 3 đơn vị; dòng tiền phân tán; khoảng 1.200 lệnh chi nhà cung cấp/tháng | Intent, Product, Operations |
| Hệ thống | ERP có khả năng xuất file; API integration chưa xác nhận | Product, Operations; API Banking là alternative |
| Nhu cầu | Payroll + supplier payment + cash management + working capital 20 tỷ/6 tháng | Intent, Planner, Product |
| Hồ sơ sẵn có | Đăng ký doanh nghiệp hợp lệ | Legal, Evidence |
| Hồ sơ thiếu | UBO và BCTC năm gần nhất | Legal blocking cho nhánh tín dụng |
| Kết quả kỳ vọng | Giao dịch: ready_to_prepare; tín dụng: pending_information; email/checklist ở dạng draft | Workflow, Operations, Approval |
| Nhóm | Field bắt buộc | Nguồn ưu tiên | MVP hero value |
| --- | --- | --- | --- |
| Nhân viên | employee_id, role, branch_id, permission_scopes | SSO/IAM mock | RM-999; Corporate RM; BR-HN-01; case:read/draft/approve |
| Workspace | active_customer_id, active_case_id, screen, selected_product_ids | UI session | COMP-ABC; CORP-DEMO-001; sales-case; [] |
| Công việc | current_task, due_at, previous_artifact_ids | CRM/task mock | discovery; ngày demo; chưa có artifact |
| Hội thoại | last_user_message, last_confirmed_intent, answered_slots | Conversation state | Yêu cầu bán hàng; chưa confirm; slots từ CRM |
| Freshness | source_updated_at, loaded_at, stale_after, is_stale | Context service | realtime/session cho workspace; TTL theo source |
| Quyền | customer_scope_allowed, document_scope_allowed | IAM policy | true cho COMP-ABC; fail-closed nếu không xác minh |
| Khối dữ liệu | Trường cần thu thập | Bắt buộc ở MVP | Cách điền hiệu quả |
| --- | --- | --- | --- |
| Định danh doanh nghiệp | tax_code, legal_name, industry, legal_type, operating_years | tax_code, name, industry | CRM trước; registry dùng verify/enrichment |
| Quy mô | employees_count, annual_revenue, branches, accounts_count | employees_count, revenue | CRM/BCTC; không hỏi lại khi còn fresh |
| Chi lương | payroll_headcount, payroll_value, pay_day, employee_account_ratio | headcount | Dùng profile làm default; hỏi pay_day sau khi chọn sản phẩm |
| Nhà cung cấp | supplier_count, payments_per_month, file_or_api, approval_levels | payments_per_month | Cho phép nêu trong câu tự nhiên; extractor chuẩn hóa |
| Dòng tiền | accounts/branches, concentration, sweeping need, reporting need | cash_flow_status | CRM + discovery; tạo Cash Management signal |
| Nhu cầu vốn | amount, tenor, purpose, expected_draw_date, collateral, contracts/invoices | amount, tenor, purpose | Thiếu BCTC/UBO vẫn cho tạo sơ bộ nhưng block approval |
| Hệ thống | ERP/HRM, API readiness, file formats, technical contact | không bắt buộc | Chỉ hỏi sau khi API/File product trở thành candidate |
| Ưu tiên | urgency, target_date, decision_makers, contact channel | urgency | RM xác nhận trước khi soạn task/email |
| Form / owner | Input liên quan trực tiếp đến case | Output bắt buộc | Không được phép |
| --- | --- | --- | --- |
| F-03 Intent / Intent Engine | RM context + discovery + message + previous confirmations | primary_intent; secondary_intents; slots; missing_decision_fields; confidence; provenance | Tự thêm product hoặc kết luận eligibility |
| F-04 Product / Product Agent | IntentResult + company segment/size + controlled catalog/policy | recommended_bundle; alternatives; score components; prerequisites; evidence_ids | Đề xuất product ngoài catalog; ghi eligible=true |
| F-05 Eligibility / Legal | Company legal profile; UBO/KYC; documents; selected products; versioned rules | status theo từng product/branch; failed_checks; missing_documents; rule/evidence IDs | Downgrade blocking rule; tự coi unknown là pass |
| F-06 Operations / Operations | Approved candidate bundle + legal branch status + SOP/SLA + existing tasks | checklist; task drafts; CRM case draft; customer email draft; dedup keys | Tạo task/email thật; tạo trùng artifact |
| F-07 Evidence / Validator | Claims của Product/Legal/Ops + retrieved chunks + source metadata | claim_supported; source/version/section; conflict/stale flags; validation report | Xác nhận claim không có source hoặc source hết hiệu lực |
| F-08 Approval / Executor | Validated payload; actor/scope; risk; payload hash; idempotency key | preview; approval event; execution receipt; audit | Thực thi khi token sai payload, hết hạn hoặc đã dùng |
| Tập dữ liệu MVP ngày mai | Số lượng tối thiểu | Mục tiêu |
| --- | --- | --- |
| Product catalog | 6 sản phẩm | Account, eBanking, Payroll, Supplier Payment, Cash Management, Working Capital |
| Policy/SOP documents | 8–10 tài liệu ngắn | Mỗi claim quan trọng có source/version/section |
| Company profiles | 3 hồ sơ | Một hero case + hai regression cases |
| Sales conversations | 20 biến thể | Keyword, không dấu, correction, multi-intent |
| Eligibility scenarios | 12 cases | Pass, block, missing, stale, conflict |
| E2E golden cases | 10 cases | 6 normal, 2 edge, 1 adversarial, 1 tool failure |
| Security cases | 5 cases | Injection, wrong RM, approval tamper, replay, PII log |
| Field | Ý nghĩa | Ví dụ cho case hero |
| --- | --- | --- |
| scenario_id / seed | ID và seed tái lập | SCN-CORP-SALES-001 / 20260718 |
| archetype | Mẫu doanh nghiệp | manufacturing_500_staff |
| input_message | Câu RM nhập | Khách cần chi lương, trả NCC và 20 tỷ vốn mùa cao điểm |
| context_overrides | Dữ liệu đã có trong workspace/CRM | customer_id, 500 staff, 120 tỷ revenue, distributed cash flow |
| missingness | Field/document cố ý thiếu | UBO, recent BCTC |
| expected_intents | Ground truth intent | payroll; supplier_payment; cash_management; working_capital |
| expected_bundle | Ground truth product IDs | 6 controlled synthetic products |
| expected_branch_status | Kết quả theo nhánh | transaction=ready_to_prepare; credit=pending_information |
| expected_artifacts | Checklist/draft/task | 3 missing-info tasks + 1 email draft |
| forbidden_actions | Hành động không được xảy ra | approve_credit; send_email; create_live_crm_without_approval |
| evidence_expectation | Nguồn bắt buộc | product/rule/SOP IDs và version khớp |
| Loại dữ liệu hiện có | Ví dụ nguồn thị trường | Khả dụng thực tế | Vai trò đúng trong solution |
| --- | --- | --- | --- |
| Đăng ký pháp nhân Việt Nam | Cổng thông tin quốc gia về đăng ký doanh nghiệp | Public search và information services; bulk/API cần xác minh quyền/kênh | Verify tên, mã số, địa chỉ, đại diện, tình trạng; không thay hồ sơ KYC nội bộ |
| Văn bản pháp luật | CSDL quốc gia về văn bản pháp luật; SBV publications | Public web/documents; cần theo dõi hiệu lực và văn bản thay thế | Legal RAG/reference; rule quan trọng vẫn được Legal owner mã hóa và ký nhận |
| Thống kê ngành/vĩ mô | NSO/NSDP; SBV statistics | Public aggregate data | Context và benchmark; không quyết định eligibility của một doanh nghiệp |
| Legal entity toàn cầu | GLEIF API/Golden Copy; OpenCorporates | GLEIF mở và cập nhật thường xuyên; OpenCorporates theo license/plan | Entity resolution, ownership enrichment, cross-border context |
| Danh sách chế tài | UN Consolidated List; OFAC SLS | Public XML/HTML/PDF; cập nhật biến động | Screening candidate; cần fuzzy matching, threshold và human review false positive |
| Thông tin tín dụng | CIC | Không phải open data; chỉ qua quyền/kênh nghiệp vụ được cấp | Live tool cho credit assessment; không lưu vào RAG chung |
| Dữ liệu doanh nghiệp thương mại | FiinGroup, D&B, Moody's/Orbis | Licensed; coverage/field/freshness/cost phụ thuộc hợp đồng | Financial/company enrichment ở shadow mode trước khi dùng quyết định |
| KYC/AML/adverse media | LSEG Risk Intelligence và vendor tương đương | Licensed; cần POC recall/precision, explainability và review queue | Risk signal; không auto-reject chỉ từ fuzzy match |
| Dữ liệu nội bộ ngân hàng | CRM, Core, DMS, transaction, task, product/policy/SOP | Giá trị cao nhất nhưng phụ thuộc owner, IAM, API và chất lượng | Nguồn quyết định chính cho context, product, eligibility và operations |
| Agent/module | Gold dataset | Xử lý đặc thù | Quality gate trước serving |
| --- | --- | --- | --- |
| Context/Intent | employee_workspace_snapshot; customer_360; conversation_state | Freshness, precedence, conflict, minimization, PII masking | No cross-case leak; required IDs; source/confidence/confirmed |
| Product | product_master; product_policy_chunks; compatibility graph | Structure-aware parse, version/effective dates, controlled vocabulary, hybrid index | Active version only; product/source linkage 100%; retrieval golden pass |
| Legal/Eligibility | rule_registry; legal_chunks; KYC/UBO/document status | Deterministic operators, severity, on_unknown, validity windows, watchlist matching | Unsafe pass=0; every blocking rule has evidence and owner |
| Operations | workflow/SOP; SLA/calendar; templates; existing task fingerprints | Step order, precondition, owner, dedup key, idempotency | No duplicate task; template variables complete; no send permission |
| Evidence | evidence_items; source manifests; claim-source links | Quote/section validation, staleness/conflict detection | Important claim support=100%; stale/conflict blocks |
| Approval/Audit | payload snapshots; approval events; execution receipts | Hash, nonce, expiry, actor/scope, sanitized logs | Payload equality; one-time use; replay blocked |
| Evaluation | golden scenarios; expected outputs/actions; adjudication | Seed/version, difficulty, risk, provenance, reviewer agreement | Schema pass; label review; no train/test leakage |
| Nguồn | Định dạng | Metadata bắt buộc |
| --- | --- | --- |
| Product catalog | PDF/Excel/DB | product_id, family, segment, version, owner |
| Product policy | PDF/Word | effective_from/to, status, rule links, ACL |
| Fee/limit tables | Excel/table | currency, unit, version, effective date |
| FAQ/Sales guide | Docs | audience, scope, product mapping |
| Status | Điều kiện |
| --- | --- |
| passed | Tất cả blocking rules pass và dữ liệu bắt buộc còn fresh |
| failed | Có rule loại trừ rõ ràng |
| pending_information | Thiếu hoặc stale input/document bắt buộc |
| pending_review | Policy conflict, PEP/AML, dữ liệu mâu thuẫn hoặc ngoại lệ pháp lý |
| Node | Đọc | Ghi / outcome |
| --- | --- | --- |
| collect_context | request/session | ContextSnapshot hoặc access/availability error |
| extract_intent / resolve_slots | message + minimized context | IntentResult, confidence, clarification |
| route_complexity / plan_tasks | intent | route, typed DAG, dependency |
| retrieve_products | intent/context | product candidates + evidence |
| evaluate_eligibility | product/context/docs | rule results + missing/blocking |
| validate_evidence | claims/evidence | valid/invalid flags; re-retrieve/review |
| prepare_operations / dedup | validated results + existing artifacts | drafts + reuse/update/create decision |
| await_approval / execute | frozen payload + token | approved action result + audit |
| Failure | Retry | Giới hạn / điều kiện |
| --- | --- | --- |
| Model timeout/5xx | Có | 2 lần, exponential backoff |
| Schema parse | Repair | 1 lần, sau đó fallback/typed error |
| Read tool timeout | Có nếu an toàn | 1 lần, cache fallback |
| Write tool timeout | Chỉ có idempotency | Query status trước retry |
| Permission denied | Không | Fail closed |
| Invalid evidence | Không retry action | Re-retrieve một lần hoặc review |
| Thay đổi | Resume | Giữ lại |
| --- | --- | --- |
| UBO/BCTC mới | Eligibility → Evidence → Operations | Context, intent, product |
| Đổi customer | Context → toàn bộ downstream | Audit |
| Đổi mục tiêu | Intent → toàn bộ downstream | Employee context |
| Catalog version mới | Product → Eligibility → downstream | Context/intent |
| RM sửa email | Approval payload | Analysis results |
| Artifact hiện có | Input/version | Hành động |
| --- | --- | --- |
| Active task | Giống | Reuse/attach |
| Active task | Khác | Update nếu cho phép; nếu không tạo linked revision |
| Completed task | Còn validity | Reuse result |
| Completed task | Stale | Tạo mới với supersedes link |
| Email draft chưa gửi | Cùng purpose | Update draft hiện có |
| CRM case active | Cùng request | Append/update, không create duplicate |
| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | /api/v2/context/current | Context employee/workspace hiện tại |
| POST | /api/v2/context/resolve | Assemble context cho message |
| POST/GET | /api/v2/cases | Tạo analysis case / đọc state |
| POST | /api/v2/cases/{id}/messages | Yêu cầu hoặc clarification answer |
| POST | /api/v2/cases/{id}/documents | Đăng ký/upload metadata tài liệu |
| PATCH | /api/v2/cases/{id}/context | Sửa context + reason + expected version |
| POST | /api/v2/cases/{id}/resume | Server tính impacted nodes và resume |
| POST | /api/v2/cases/{id}/approval-preview | Freeze payload + diff |
| POST | /api/v2/cases/{id}/approve|execute|reject | HITL và action có kiểm soát |
| GET | /api/v2/cases/{id}/trace | User-safe timeline; không hiển thị hidden CoT |
| Store/Table | Mục đích |
| --- | --- |
| cases / case_state_versions | Current index + immutable versioned state/hash |
| workflow_tasks | DAG node, dedup key, status, input/output hash |
| context_values | Field-level provenance, confidence, freshness |
| artifacts | Checklist/email/brief/case/task drafts theo version/hash |
| approval_tokens / idempotency_records | One-time approval và side-effect dedup |
| audit_events | Append-only hash chain, actor/action/state versions |
| Vector DB | Product/legal chunks + ACL/effective metadata |
| DMS/Object store | Source documents; không nhúng raw blob trong case state |
| Redis/cache | Context/retrieval/node caches theo TTL/version/scope |
| SLO | Mục tiêu ban đầu |
| --- | --- |
| API read availability pilot | 99.5% |
| P95 context assembly | < 2 giây, không tính upstream unavailable |
| P95 complete analysis | < 30 giây |
| Duplicate external write | 0 |
| High-risk alert emission | < 1 phút |
| Suite | Quy mô tối thiểu pilot | Mục đích |
| --- | --- | --- |
| Intent conversations | 100 | Intent/entity/context/confidence/no-repeat |
| Product RAG | 40 | Retrieval/citation/OOS/version/ACL |
| Eligibility | 40 | Rules, missing, blocking, conflict |
| E2E business | 40 | Complete journeys, artifact/action outcomes |
| Adversarial/security | 25 | Injection, RBAC, tool, token, payload |
| Reliability | 20 | Timeout, retry, cache, replay, concurrency |
| Metric | MVP gate | Pilot gate |
| --- | --- | --- |
| Contract-valid outputs | 100% | 100% |
| Primary intent accuracy | ≥ 90% | ≥ 95% |
| Multi-intent recall | ≥ 90% | ≥ 95% |
| System slot auto-fill | ≥ 98% | ≥ 99% |
| Unnecessary clarification | < 10% | < 5% |
| Product Hit@5 | ≥ 90% | ≥ 95% |
| Citation correctness | 100% important claims | 100% |
| Eligibility unsafe pass | 0% | 0% |
| Missing-document recall | ≥ 95% | 100% high-risk target |
| Duplicate task/action | 0% | 0% |
| Correct resume selection | ≥ 90% | ≥ 95% |
| Cross-scope leak | 0 | 0 |
| Metric | Cách đo | Ý nghĩa |
| --- | --- | --- |
| Task completion rate | Tỷ lệ case hoàn thành đủ product, legal và operations outputs | Đo khả năng hoàn thành workflow |
| Tool selection accuracy | Tool được gọi có đúng domain và input không | Đo khả năng hành động |
| Product relevance@K | Sản phẩm phù hợp có nằm trong top-K không | Đánh giá Product Agent |
| Eligibility accuracy | Kết quả điều kiện đúng so với đáp án mẫu | Đánh giá Legal Agent |
| Missing-information recall | Tỷ lệ dữ liệu thiếu được phát hiện | Giảm hồ sơ bổ sung muộn |
| Checklist completeness | Các tài liệu bắt buộc có được liệt kê đầy đủ | Đánh giá Operations Agent |
| Citation coverage | Tỷ lệ claim quan trọng có citation | Tăng khả năng audit |
| Unsupported claim rate | Tỷ lệ claim không có căn cứ | Đo hallucination |
| Action success rate | Case/task được tạo đúng và không trùng | Đo thực thi |
| Latency & cost | Thời gian và token/case | Chứng minh adaptive routing |
| Human override rate | Tỷ lệ RM phải sửa hoặc từ chối đề xuất | Đo độ tin cậy thực tế |
| ID | Task | Depends | Done when |
| --- | --- | --- | --- |
| V2-001 | Contracts/models | — | JSON/Pydantic/API examples đồng nhất |
| V2-002–003 | Employee/workspace context + assembler | 001 | Source/freshness đủ; no cross-case leak |
| V2-004–005 | Intent + slots/confidence/clarification | 001–003 | Structured outputs; no-repeat target |
| V2-006–007 | Ingestion/index + hybrid retrieval/matcher | 001,004 | Index reproducible; Hit@5/citation đạt gate |
| V2-008 | Eligibility/Legal | 001,007 | Blocking/evidence đúng; unsafe pass 0 |
| V2-009 | Workflow/state/resume | 005,008 | DAG/retry/impact selection đúng |
| V2-010 | Operations/dedup/artifacts | 009 | No duplicate artifacts/tasks |
| V2-011 | Safety/approval/executor | 001,009,010 | No unsafe/duplicate write |
| V2-012 | Storage/observability | 001,009,011 | Restart-safe pilot profile, sanitized trace |
| V2-013 | API/UI | 002–012 | Complete ABC journey qua UI |
| V2-014–015 | Evaluation + E2E hardening | All | Thresholds đo được; acceptance system pass |
| Giai đoạn | Deliverables | Gate ra |
| --- | --- | --- |
| 1. Contracts & Context | Schema, shared state, IAM/workspace/CRM mock, context header | Auto-fill ≥98%, leak=0 |
| 2. Intent & Product RAG | Taxonomy, extractor, clarification, ingestion/index/retrieval | Intent/RAG gates MVP |
| 3. Eligibility & Workflow | Rule registry, Legal RAG, DAG/state/resume | Unsafe pass=0; resume ≥90% |
| 4. Operations & Approval | Checklist/draft/dedup, token/executor | Duplicate/unsafe action=0 |
| 5. Persistence/UI/Eval | PostgreSQL/vector DB, observability, UI E2E, datasets | System acceptance pass |
| 6. Pilot | 5–10 RM, sandbox integrations, feedback/quality dashboard | Pilot gates + governance sign-off |
| Hạng mục | Baseline đã có | V2 còn cần |
| --- | --- | --- |
| Shared state | Pydantic MVP | JSON contract V2 + provenance + migration |
| Planner | Deterministic DAG | Nối Context/Intent + impact resume |
| Product retrieval | Hash embedding, in-memory hybrid-lite | PDF/Excel ingestion, persistent hybrid index, ACL/version |
| Product module | Deterministic MVP | Intent contract, matcher/evidence versioning |
| Legal | Synthetic rules | Rule registry + Legal RAG + effective dates |
| Operations | Checklist/email draft | Artifact reuse, dedup, partial update |
| Approval | HMAC demo | Payload hash, nonce, expiry, one-time use, RBAC |
| API/UI | FastAPI + demo UI | Context endpoints, correction, intent/evidence/approval panels |
| Storage/index | In-memory/local demo | PostgreSQL, vector DB, Redis, migrations |
| Tests | 73 tests pass; gồm baseline + V2 contracts/context | MVP golden data cho corporate sales + UI E2E + demo smoke test |
| Rủi ro | Biểu hiện | Kiểm soát |
| --- | --- | --- |
| Prompt chaining giả multi-agent | Ba agent cùng trả lời rồi ghép text | Dependency, shared state, tool calls và action phải thay đổi theo kết quả agent khác. |
| Hallucination | Kết luận không có nguồn | Evidence Validator, citation coverage và abstain khi thiếu evidence. |
| Dữ liệu nhạy cảm | Dùng hồ sơ thật trong hackathon | Chỉ dùng synthetic data, masking và role-based access. |
| Tool misuse | Agent tự tạo case hoặc đổi trạng thái | Allowed-tool registry, human approval và idempotency key. |
| Workflow quá phức tạp | Nhiều agent/loop làm demo lỗi | Giữ Planner + 3 specialist, controlled graph, giới hạn retry. |
| Domain sai | Điều kiện sản phẩm/pháp lý không chính xác | Dữ liệu mẫu có đáp án chuẩn, rule deterministic và expert review. |
| Latency/cost cao | Mọi câu hỏi đều chạy 3 agent | Complexity Router và parallel execution khi phù hợp. |
| Dataset | MVP | Pilot / owner |
| --- | --- | --- |
| Product catalog/policies | Synthetic 5–10 products/rules | Catalog + policy version được Product/Risk ký nhận |
| Legal/KYC/AML | Synthetic 3–5 rules | Current policies + Legal/Compliance owner |
| SOP/SLA | Synthetic templates | Approved SOP/business calendar từ Operations |
| Employee/IAM | Mock roles/scopes | SSO/IAM spec từ IT/Security |
| CRM/DMS/task | Synthetic companies/adapters | Sandbox schema/API + idempotency/status query |
| Conversations/eval | Curated synthetic | De-identified samples + dual-reviewed high-risk labels |
| Domain | Tool/API | Chức năng |
| --- | --- | --- |
| Shared | get_company_profile(customer_id) | Lấy hồ sơ doanh nghiệp có cấu trúc. |
| Product | search_product_catalog(criteria) | Tìm ứng viên sản phẩm. |
| Product | retrieve_product_policy(product_id, query) | Tra cứu điều kiện và tài liệu sản phẩm. |
| Product | rank_products(profile, candidates) | Xếp hạng và giải thích mức phù hợp. |
| Legal | validate_business_registration(document) | Kiểm tra trường bắt buộc và hiệu lực. |
| Legal | check_representative_and_ubo(profile) | Kiểm tra người đại diện và UBO. |
| Legal | check_product_eligibility(product_id, legal_profile) | Đối chiếu điều kiện pháp lý. |
| Legal | search_compliance_policy(query) | Tra cứu căn cứ và citation. |
| Operations | get_required_documents(product_ids, profile) | Lấy checklist hồ sơ. |
| Operations | check_document_completeness(required, available) | Xác định hồ sơ thiếu. |
| Operations | create_case(payload) | Tạo case sau phê duyệt. |
| Operations | create_followup_task(case_id, task) | Tạo task và gán owner. |
| Operations | draft_customer_email(context) | Soạn nội dung yêu cầu bổ sung. |
| Shared | export_decision_brief(case_id) | Xuất báo cáo PDF/DOCX/Markdown. |
| Bước | Nhiệm vụ |
| --- | --- |
| 1. Xác định contract | Định nghĩa phạm vi, input schema, output schema, tool được phép gọi và điều kiện dừng. |
| 2. Chuẩn bị dữ liệu | Thu thập, chuẩn hóa, gắn metadata, phân quyền và tạo bộ dữ liệu giả lập. |
| 3. Xây knowledge retrieval | Chunking, embedding, metadata filter, reranking và citation. |
| 4. Xây tools | API/function có schema rõ, validation, error handling và audit event. |
| 5. Viết system prompt | Vai trò, giới hạn, quy tắc evidence, cách xử lý thiếu dữ liệu và format output. |
| 6. Tích hợp workflow node | Đọc shared state, gọi tool, ghi output vào state và phát event. |
| 7. Validation | Pydantic/JSON schema, rule deterministic và evidence check. |
| 8. Agent-level evaluation | Test retrieval, tool selection, completeness, unsupported claim và latency. |
| 9. Observability | Trace, token/cost, tool calls, lỗi, retry và thời gian từng node. |
| 10. Definition of Done | Agent chạy ổn định trên bộ test, không vượt quyền, output đúng schema và có evidence. |
| ID | Nhiệm vụ | Kết quả mong đợi |
| --- | --- | --- |
| P1 | Thiết kế intent/complexity classifier | Phân biệt tra cứu đơn giản, workflow phức tạp và case rủi ro cao. |
| P2 | Thiết kế execution plan schema | Task ID, owner agent, inputs, dependency, status, retry và expected output. |
| P3 | Xây agent capability registry | Khai báo phạm vi và tool được phép của Product, Legal và Operations. |
| P4 | Xây dependency engine | Cho phép tuần tự, song song có điều kiện, pause và resume. |
| P5 | Xây shared state | Lưu request, agent outputs, evidence, tasks, errors và approval. |
| P6 | Xây missing-information loop | Tổng hợp dữ liệu thiếu, sinh Next Best Question và quay lại workflow sau khi bổ sung. |
| P7 | Xây escalation logic | Ngoại lệ, confidence thấp hoặc xung đột chính sách phải chuyển human review. |
| P8 | Xây final synthesis | Tạo decision brief nhưng không sửa trái kết luận của specialist agent. |
| P9 | Test adaptive routing | Case đơn chỉ dùng RAG; case phức tạp mới kích hoạt multi-agent. |
| P10 | Test failure handling | Tool timeout, output sai schema, agent fail và resume workflow. |
| ID | Nhiệm vụ | Kết quả mong đợi |
| --- | --- | --- |
| PR1 | Xây company-needs normalizer | Chuẩn hóa nhu cầu thành các tiêu chí: thanh toán, dòng tiền, payroll, vốn, bảo lãnh... |
| PR2 | Chuẩn hóa product catalog | Product ID, segment, features, conditions, fees, limits, source metadata. |
| PR3 | Xây Product RAG | Metadata filter theo phân khúc/nhu cầu và citation theo tài liệu sản phẩm. |
| PR4 | Xây candidate retrieval | Lấy top-N sản phẩm phù hợp trước khi LLM reasoning. |
| PR5 | Xây matching/ranking | Tính match score dựa trên nhu cầu, eligibility sơ bộ và missing information. |
| PR6 | Xây solution bundle logic | Ghép nhiều sản phẩm thành phương án doanh nghiệp hoàn chỉnh. |
| PR7 | Xây question generator | Hỏi những dữ liệu có thể thay đổi ranking: volume, nhân sự, thị trường, dòng tiền. |
| PR8 | Xây output schema | Recommended products, reasons, conditions, missing data, evidence và confidence. |
| PR9 | Xây tool calls | search_product_catalog, retrieve_product_policy, compare_products, rank_products. |
| PR10 | Đánh giá | Top-k relevance, explanation groundedness, citation coverage và bundle completeness. |
| ID | Nhiệm vụ | Kết quả mong đợi |
| --- | --- | --- |
| L1 | Xây document classifier/extractor | Nhận diện loại hồ sơ, trích trường và ngày hiệu lực. |
| L2 | Xây legal profile schema | Pháp nhân, người đại diện, ủy quyền, UBO, trạng thái KYC. |
| L3 | Chuẩn hóa compliance policy | Rule ID, severity, required evidence, escalation owner. |
| L4 | Xây Legal RAG | Tra cứu policy/văn bản theo điều kiện cụ thể, có citation và version. |
| L5 | Xây deterministic checks | Missing field, expiry, mismatch và required document checks. |
| L6 | Xây product eligibility checker | Đối chiếu sản phẩm Product Agent đề xuất với hồ sơ pháp lý. |
| L7 | Xây ambiguity/conflict detector | Flag khi hai nguồn mâu thuẫn hoặc không đủ căn cứ. |
| L8 | Xây risk classification | Low/medium/high và điều kiện human review. |
| L9 | Xây output schema | Passed checks, issues, missing data, evidence, risk và review requirement. |
| L10 | Đánh giá | Eligibility accuracy, missing-data recall, citation accuracy và unsafe approval rate. |
| ID | Nhiệm vụ | Kết quả mong đợi |
| --- | --- | --- |
| O1 | Chuẩn hóa workflow/SOP | Step, precondition, owner, SLA, transition và required documents. |
| O2 | Xây checklist resolver | Tạo checklist theo sản phẩm, phân khúc và kết quả Legal Agent. |
| O3 | Xây completeness checker | So sánh required vs available documents và trả missing items. |
| O4 | Xây state transition engine | new → in_review → pending_information → pending_approval → completed. |
| O5 | Xây case/task tools | create_case, create_task, assign_owner, update_status. |
| O6 | Xây draft generator | Email yêu cầu bổ sung, memo nội bộ, checklist khách hàng và report. |
| O7 | Xây SLA/deadline calculator | Tạo deadline và cảnh báo trễ theo loại task. |
| O8 | Xây approval-aware execution | Chỉ gọi action executor khi RM đã approve. |
| O9 | Xây idempotency/error handling | Không tạo trùng case/task khi retry hoặc refresh. |
| O10 | Đánh giá | Checklist completeness, correct status transition, task accuracy và action success rate. |
| ID | Nhiệm vụ | Kết quả mong đợi |
| --- | --- | --- |
| V1 | Claim extraction | Tách các kết luận quan trọng từ output của từng agent. |
| V2 | Citation verifier | Kiểm tra citation có đúng tài liệu, section và hỗ trợ claim. |
| V3 | Effective-date verifier | Chặn hoặc cảnh báo nguồn hết hiệu lực. |
| V4 | Unsupported-claim detector | Loại bỏ hoặc chuyển review các claim không có evidence. |
| V5 | Policy rule engine | Các rule cứng: không auto-approve, thiếu UBO phải pause, high risk phải review. |
| V6 | Approval UI | RM xem action, căn cứ, rủi ro; approve/reject/edit. |
| V7 | Immutable audit event | Lưu ai phê duyệt, khi nào, action nào và evidence nào. |
| V8 | Red-team tests | Prompt injection, data exfiltration, tool misuse và action vượt quyền. |
| Nhóm dữ liệu | Nội dung tối thiểu | Mục đích | Mức nhạy cảm |
| --- | --- | --- | --- |
| Enterprise Profile | Mã khách hàng, loại hình, ngành nghề, quy mô, địa điểm, doanh thu, số nhân viên, nhu cầu | Cung cấp context cho Planner và Product Agent | Nội bộ / có thể chứa dữ liệu cá nhân |
| Customer Request | Mục tiêu, ưu tiên, deadline, ghi chú RM, sản phẩm đang dùng | Xác định goal và phân rã task | Nội bộ |
| Uploaded Documents | Tên file, loại file, ngày phát hành, ngày hết hạn, nguồn, trạng thái đọc | Phục vụ Legal và Operations | Nhạy cảm |
| Case History | Trao đổi trước, task đã tạo, kết quả review, trạng thái case | Tránh hỏi lặp và hỗ trợ audit | Nhạy cảm |
| Source Metadata | Document ID, version, effective date, owner, permission, page/section | Citation và kiểm soát hiệu lực | Nội bộ |
| Dữ liệu | Trường/thuộc tính nên có | Vai trò |
| --- | --- | --- |
| Case context | request_id, customer_id, RM note, priority, SLA | Hiểu mục tiêu và bối cảnh |
| Task taxonomy | task type, domain, required inputs, expected output | Tạo kế hoạch có cấu trúc |
| Agent capability registry | agent name, scope, allowed tools, input/output schema | Giao đúng task cho đúng agent |
| Dependency rules | T1 trước T2; điều kiện pause/retry/skip | Quản lý luồng và dependency graph |
| Risk policy | risk level, escalation owner, approval requirement | Quyết định dừng hoặc chuyển người |
| Execution history | task status, retries, errors, tool outputs | Tiếp tục/resume workflow và tránh lặp |
| Nhóm dữ liệu | Trường quan trọng | Cách sử dụng |
| --- | --- | --- |
| Hồ sơ doanh nghiệp | Ngành nghề, quy mô, doanh thu, số nhân viên, luồng tiền, thị trường, nhu cầu vốn | Hiểu bối cảnh và phân khúc |
| Nhu cầu khách hàng | Mục tiêu, pain point, ưu tiên chi phí/tốc độ/kiểm soát, kênh giao dịch | Chuyển nhu cầu thành tiêu chí matching |
| Product catalog | Product ID, tên, mô tả, phân khúc, chức năng, prerequisite | Tìm sản phẩm ứng viên |
| Product policy | Điều kiện, giới hạn, đối tượng, loại trừ, tài liệu yêu cầu | Giải thích và lọc sản phẩm |
| Pricing/limits | Phí, hạn mức, SLA, thời gian triển khai, kênh hỗ trợ | So sánh phương án |
| Bundles/use cases | Các gói hoặc tổ hợp sản phẩm theo nhu cầu | Tạo solution bundle thay vì một sản phẩm rời |
| Document metadata | Version, effective date, owner, source | Tránh dùng tài liệu hết hiệu lực |
| Case feedback (tùy chọn) | Sản phẩm được RM chấp nhận/từ chối và lý do | Cải thiện ranking và đánh giá |
| Nhóm dữ liệu | Trường quan trọng | Cách sử dụng |
| --- | --- | --- |
| Hồ sơ pháp nhân | Đăng ký doanh nghiệp, loại hình pháp nhân, mã số thuế, ngành nghề | Kiểm tra tư cách và phạm vi hoạt động |
| Người đại diện/ủy quyền | Thông tin người đại diện, giấy ủy quyền, phạm vi và hiệu lực | Kiểm tra thẩm quyền giao dịch |
| UBO/KYC | Chủ sở hữu hưởng lợi, cơ cấu sở hữu, thông tin nhận diện | Kiểm tra mức độ đầy đủ của KYC |
| Document validity | Ngày cấp, hết hạn, trạng thái xác minh, bản cập nhật | Phát hiện giấy tờ hết hiệu lực |
| Compliance policies | KYC/AML, onboarding, phân loại rủi ro, quy tắc ngoại lệ | Đối chiếu điều kiện nội bộ |
| Product eligibility | Điều kiện pháp lý theo từng sản phẩm | Kiểm tra đề xuất từ Product Agent |
| Watchlist/PEP/sanction mock | Kết quả kiểm tra giả lập, trạng thái match, reviewer | Minh họa luồng kiểm soát; không dùng dữ liệu thật trong MVP |
| Legal sources | Văn bản pháp luật/quy định, điều khoản, ngày hiệu lực | Citation và giải thích căn cứ |
| Nhóm dữ liệu | Trường quan trọng | Cách sử dụng |
| --- | --- | --- |
| Required document checklist | Theo sản phẩm, loại doanh nghiệp, phân khúc và ngoại lệ | So sánh hồ sơ cần có với hồ sơ hiện có |
| SOP/workflow definition | Các bước, điều kiện chuyển trạng thái, dependency | Xác định next action |
| Case status model | new, in_review, pending_information, pending_approval, completed, rejected | Cập nhật trạng thái nhất quán |
| RACI/owner directory | Bộ phận, vai trò, người phụ trách, quyền phê duyệt | Gán task đúng owner |
| SLA/deadline rules | Thời gian xử lý theo task/product/risk level | Tính deadline và cảnh báo |
| Templates | Email yêu cầu bổ sung, checklist, memo, report | Tạo nội dung có chuẩn |
| Integration schema | CRM/case/task API, required fields, error codes | Thực hiện action nghiệp vụ |
| Operational history | Task cũ, lỗi phổ biến, thời gian thực tế | Theo dõi tiến độ và tối ưu quy trình |
| Dữ liệu | Cần lưu | Kiểm tra |
| --- | --- | --- |
| Claim-evidence mapping | Claim ID, evidence ID, page/section, quote span | Mỗi kết luận quan trọng có nguồn hay không |
| Document lifecycle | Version, effective date, superseded_by, owner | Nguồn còn hiệu lực hay đã bị thay thế |
| Confidence & risk | Model confidence, retrieval score, severity | Xác định cần hỏi thêm hay chuyển review |
| Policy rules | Forbidden action, required approval, mandatory fields | Chặn action sai quyền hoặc thiếu điều kiện |
| Validation history | Pass/fail, reviewer, reason, timestamp | Audit và đánh giá chất lượng |
| Giai đoạn | Doanh nghiệp thường cần |
| --- | --- |
| Mới thành lập | Tài khoản, ngân hàng số, nộp thuế, thanh toán cơ bản |
| Bắt đầu có nhân sự | Chi lương, phân quyền, quản lý giao dịch |
| Tăng trưởng | Vốn lưu động, thu hộ/chi hộ, cash management |
| Mở rộng | Vay đầu tư, bảo lãnh, tài trợ dự án |
| Xuất nhập khẩu | Thanh toán quốc tế, ngoại hối, trade finance |
| Quy mô lớn | API banking, ERP integration, quản lý thanh khoản tập trung |
| Sản phẩm | Chức năng |
| --- | --- |
| Tài khoản thanh toán doanh nghiệp | Nhận tiền, chuyển tiền, thanh toán và quản lý số dư |
| Tài khoản chuyên thu | Nhận tiền từ khách hàng, đại lý hoặc điểm bán |
| Tài khoản chuyên chi | Kiểm soát các khoản thanh toán riêng biệt |
| Tài khoản vốn đầu tư | Phục vụ hoạt động đầu tư theo yêu cầu pháp lý |
| Tài khoản ngoại tệ | Nhận, giữ và thanh toán bằng ngoại tệ |
| Tài khoản ký quỹ | Phục vụ bảo lãnh, hợp đồng hoặc nghĩa vụ tài chính |
| Tiền gửi có kỳ hạn doanh nghiệp | Tối ưu dòng tiền tạm thời chưa sử dụng |
| Sản phẩm | Chức năng |
| --- | --- |
| Internet Banking doanh nghiệp | Quản lý tài khoản và giao dịch trực tuyến |
| Mobile Banking doanh nghiệp | Theo dõi và phê duyệt giao dịch trên điện thoại |
| Phân quyền giao dịch nhiều cấp | Người lập, người kiểm soát, người phê duyệt |
| Chuyển tiền hàng loạt | Thanh toán nhiều giao dịch cùng lúc |
| Quản lý người dùng doanh nghiệp | Tạo tài khoản và phân quyền nhân viên |
| Thông báo biến động số dư | Theo dõi giao dịch theo thời gian thực |
| API Banking | Kết nối ngân hàng với ERP hoặc phần mềm kế toán |
| Sản phẩm | Chức năng |
| --- | --- |
| Cash Management | Quản lý dòng tiền tập trung |
| Quản lý nhiều tài khoản | Tổng hợp số dư và giao dịch |
| Cash Pooling | Tập trung hoặc điều chuyển tiền giữa các tài khoản |
| Sweeping tự động | Tự động chuyển tiền theo ngưỡng |
| Quản lý thanh khoản | Theo dõi dòng tiền thiếu hoặc dư |
| Báo cáo dòng tiền | Tổng hợp dòng tiền theo tài khoản và đơn vị |
| Dự báo dòng tiền | Hỗ trợ lập kế hoạch thanh khoản |
| Sản phẩm | Chức năng |
| --- | --- |
| Thu hộ qua tài khoản định danh | Nhận biết tiền đến từ khách hàng hoặc đơn hàng nào |
| Virtual Account | Cấp tài khoản định danh cho từng khách hàng |
| Thu hộ qua QR | Thu tiền bằng mã QR |
| Thu hộ hóa đơn | Thu học phí, phí dịch vụ hoặc hóa đơn định kỳ |
| Direct Debit | Tự động thu tiền theo ủy quyền |
| Payment Link | Tạo đường dẫn thanh toán |
| Đối soát tự động | Ghép giao dịch ngân hàng với hóa đơn hoặc đơn hàng |
| Sản phẩm | Chức năng |
| --- | --- |
| Chi hộ hàng loạt | Thanh toán cho nhiều người nhận |
| Thanh toán nhà cung cấp | Quản lý khoản phải trả |
| Thanh toán hóa đơn | Điện, nước, viễn thông và dịch vụ |
| Thanh toán định kỳ | Tự động xử lý khoản chi lặp lại |
| File Payment | Tải danh sách giao dịch từ ERP hoặc Excel |
| API Payment | Gửi lệnh thanh toán trực tiếp từ hệ thống doanh nghiệp |
| Kiểm soát phê duyệt | Phân quyền người lập và người duyệt |
| Sản phẩm | Chức năng |
| --- | --- |
| Payroll Service | Trả lương hàng loạt |
| Mở tài khoản cho nhân viên | Tạo tài khoản nhận lương |
| Chi thưởng và phụ cấp | Thực hiện các khoản chi ngoài lương |
| Tích hợp phần mềm HRM | Đồng bộ dữ liệu từ hệ thống nhân sự |
| Báo cáo kết quả chi lương | Theo dõi giao dịch thành công hoặc thất bại |
| Gói phúc lợi nhân viên | Dịch vụ bổ sung cho nhân viên doanh nghiệp |
| Sản phẩm | Mục đích |
| --- | --- |
| Hạn mức tín dụng ngắn hạn | Bổ sung vốn hoạt động thường xuyên |
| Vay vốn lưu động | Mua nguyên liệu, hàng hóa và trả chi phí |
| Thấu chi tài khoản | Bù thiếu hụt dòng tiền ngắn hạn |
| Cho vay theo hợp đồng | Thực hiện đơn hàng hoặc hợp đồng |
| Cho vay theo hóa đơn | Bổ sung vốn trong thời gian chờ thu tiền |
| Chiết khấu khoản phải thu | Chuyển khoản phải thu thành dòng tiền sớm |
| Tài trợ nhà phân phối | Hỗ trợ vốn cho doanh nghiệp phân phối |
| Tài trợ nhà cung cấp | Hỗ trợ vốn trong chuỗi cung ứng |
| Sản phẩm | Mục đích |
| --- | --- |
| Vay mua máy móc thiết bị | Đầu tư dây chuyền sản xuất |
| Vay mua phương tiện | Mua xe hoặc phương tiện vận tải |
| Vay xây dựng nhà xưởng | Mở rộng cơ sở sản xuất |
| Vay đầu tư dự án | Tài trợ dự án kinh doanh |
| Vay mở rộng chi nhánh | Mở rộng mạng lưới hoạt động |
| Tài trợ công nghệ | Đầu tư phần mềm và chuyển đổi số |
| Sản phẩm | Mục đích |
| --- | --- |
| Bảo lãnh dự thầu | Tham gia đấu thầu |
| Bảo lãnh thực hiện hợp đồng | Đảm bảo thực hiện nghĩa vụ hợp đồng |
| Bảo lãnh tạm ứng | Đảm bảo khoản tiền tạm ứng |
| Bảo lãnh thanh toán | Đảm bảo nghĩa vụ thanh toán |
| Bảo lãnh bảo hành | Đảm bảo trách nhiệm bảo hành |
| Bảo lãnh hoàn trả | Hoàn trả khoản tiền theo điều kiện hợp đồng |
| Bảo lãnh vay vốn | Đảm bảo nghĩa vụ vay |
| Sản phẩm | Chức năng |
| --- | --- |
| Chuyển tiền quốc tế | Thanh toán hoặc nhận tiền xuyên biên giới |
| Thư tín dụng nhập khẩu | Cam kết thanh toán cho nhà xuất khẩu |
| Thư tín dụng xuất khẩu | Nhận và xử lý LC |
| Nhờ thu nhập khẩu | Thanh toán dựa trên bộ chứng từ |
| Nhờ thu xuất khẩu | Thu tiền từ đối tác nước ngoài |
| Tài trợ nhập khẩu | Cấp vốn mua hàng từ nước ngoài |
| Tài trợ xuất khẩu | Bổ sung vốn sản xuất hàng xuất khẩu |
| Chiết khấu bộ chứng từ | Nhận tiền trước khi đối tác thanh toán |
| Tài trợ trước giao hàng | Vốn sản xuất hàng xuất khẩu |
| Tài trợ sau giao hàng | Vốn trong thời gian chờ thanh toán |
| Sản phẩm | Chức năng |
| --- | --- |
| Mua bán ngoại tệ giao ngay | Thanh toán giao dịch hiện tại |
| Hợp đồng kỳ hạn | Cố định tỷ giá cho giao dịch tương lai |
| Hoán đổi ngoại tệ | Quản lý nhu cầu ngoại tệ theo kỳ hạn |
| Tư vấn rủi ro tỷ giá | Hỗ trợ kiểm soát biến động tỷ giá |
| Chuyển đổi ngoại tệ | Đổi giữa các loại tiền |
| Sản phẩm | Chức năng |
| --- | --- |
| Thẻ tín dụng doanh nghiệp | Thanh toán chi phí kinh doanh |
| Thẻ ghi nợ doanh nghiệp | Chi tiêu từ tài khoản công ty |
| Thẻ công tác | Quản lý chi phí đi lại |
| Thẻ mua hàng | Mua nguyên vật liệu hoặc dịch vụ |
| Hạn mức theo nhân viên | Kiểm soát mức chi |
| Báo cáo chi tiêu | Theo dõi giao dịch theo bộ phận |
| Sản phẩm | Chức năng |
| --- | --- |
| Supply Chain Finance | Tài trợ các thành viên trong chuỗi |
| Dealer Financing | Tài trợ nhà phân phối hoặc đại lý |
| Supplier Financing | Tài trợ nhà cung cấp |
| Anchor Program | Giải pháp xoay quanh doanh nghiệp đầu chuỗi |
| Dynamic Discounting | Chiết khấu theo thời gian thanh toán |
| Thu hộ đại lý | Quản lý doanh thu từ mạng lưới phân phối |
| Sản phẩm | Chức năng |
| --- | --- |
| POS | Chấp nhận thanh toán tại điểm bán |
| QR Merchant | Nhận thanh toán bằng QR |
| Payment Gateway | Thanh toán trực tuyến |
| E-commerce Collection | Thu tiền từ sàn hoặc website |
| Settlement Account | Nhận tiền quyết toán |
| Merchant Dashboard | Theo dõi doanh số và đối soát |
| Khung giờ | P0 phải hoàn thành | Artifact/acceptance |
| --- | --- | --- |
| 08:00–09:00 | Freeze case hero, 6 product IDs, 4 intents, 2 blocking documents và expected states | scenario spec + data manifest; không đổi scope sau 09:00 |
| 09:00–11:00 | Mở rộng synthetic catalog/rules/SOP; nối keyword/structured extraction tối thiểu | Product/Legal/Ops outputs dùng cùng IDs; unit tests pass |
| 11:00–12:00 | Đảm bảo partial branch: transaction tiếp tục, credit pending_information | E2E assertion cho branch status và missing UBO/BCTC |
| 13:00–15:00 | Thay raw JSON UI bằng cards: context, needs, bundle, eligibility, checklist, evidence, approval | RM hiểu kết quả trong <2 phút; không cần đọc trace JSON |
| 15:00–16:00 | Tạo 10 golden scenarios và 5 security cases | Regression runner pass; forbidden actions được assert |
| 16:00–17:00 | Demo rehearsal 3 lần từ clean start; kiểm tra restart và port | Runbook có lệnh; thời lượng demo 5–7 phút |
| 17:00–18:00 | Fix blocker, chụp backup, đóng gói README và fallback video/screenshots nếu cần | Release candidate; no critical known failure |
| ID | Scenario | Kết quả bắt buộc |
| --- | --- | --- |
| AC-01 | Context-first short request | Resolve customer/case/product từ workspace, không clarification, trả checklist |
| AC-02 | ABC multi-intent | Recommend catalog products; credit pending vì UBO/BCTC; giữ non-credit |
| AC-03 | Partial resume | Upload UBO chỉ rerun impacted nodes và update artifacts |
| AC-04 | Deduplication | Equivalent active task được reuse, không side effect thứ hai |
| AC-05 | Approval integrity | Edit làm token invalid; unchanged payload executes once despite retry |
| AC-06 | Security | Injection/tool privilege escalation bị block và audit high severity |