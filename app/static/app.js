const $ = id => document.getElementById(id);
let authToken = sessionStorage.getItem("shb_access_token") || "";
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pretty = value => typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "—");

const statusLabels = {
  draft:"Hồ sơ nháp", files_uploaded:"Đã tải file", document_processing:"Đang đọc hồ sơ",
  profile_review_required:"RM cần xác nhận", profile_confirmed:"Context đã xác nhận",
  clarification_required:"Cần làm rõ nhu cầu", pending_information:"Thiếu thông tin",
  pending_review:"Cần chuyên viên kiểm tra", pending_approval:"Chờ RM phê duyệt",
  completed:"Đã hoàn tất", rejected:"Đã từ chối", failed:"Lỗi xử lý"
};
const intentLabels = {payroll:"Chi lương",cash_management:"Quản lý dòng tiền",working_capital:"Vốn lưu động",bulk_payment:"Thu/chi hộ",product_discovery:"Tìm giải pháp"};
const profileLabels = {
  company_identity:"Định danh doanh nghiệp",business_profile:"Quy mô kinh doanh",operating_model:"Mô hình vận hành",
  transaction_profile:"Giao dịch",collection_profile:"Thu hộ",payment_profile:"Chi trả",payroll_profile:"Chi lương",
  cash_flow_profile:"Dòng tiền",technology_profile:"Công nghệ",financing_profile:"Tài chính",legal_profile:"Pháp lý"
};

const ui = {caseId:null,intakeVersion:null,stateVersion:null,intakeStatus:"draft",runtime:null,profile:null,conflicts:[],documents:[],pendingFiles:[],approvalToken:null,previewHash:null,lastPayload:{}};
const customerUi = {caseId:null,version:null,pendingFiles:[]};
const fieldLabels = {
  technical_contact_available:"Đầu mối kỹ thuật tích hợp",
  financial_statements:"Báo cáo tài chính gần nhất",
  ubo_status:"Thông tin chủ sở hữu hưởng lợi (UBO)",
  has_property_insurance:"Bảo hiểm tài sản bảo đảm",
  has_cargo_insurance:"Bảo hiểm hàng hóa vận chuyển",
  business_registration:"Đăng ký kinh doanh",
};
const domainStatusLabels = {
  not_applicable:"Không áp dụng cho case này",
  ready_for_credit_review:"Sẵn sàng để chuyên viên tín dụng thẩm định",
  ready_for_insurance_review:"Sẵn sàng để chuyên viên bảo hiểm rà soát",
  needs_information:"Cần bổ sung thông tin",
  hard_block_detected:"Có điều kiện chặn",
};
const modeLabels = {deterministic_fallback:"Rule + dữ liệu demo",llm:"LLM có cấu trúc",hybrid:"LLM + rule"};
const toolLabels = {
  product_search:"Catalog sản phẩm",
  credit_analyze_readiness:"Bộ kiểm tra tín dụng",
  insurance_analyze_readiness:"Bộ kiểm tra bảo hiểm",
};

function readableField(value){return fieldLabels[value]||String(value||"").replaceAll("_"," ")}
function humanizeText(value){
  let text=String(value||"");
  const replacements={...fieldLabels,TECHNICAL_CONTACT_NEEDED:"Thiếu đầu mối kỹ thuật tích hợp",technical_contact_available:"đầu mối kỹ thuật tích hợp"};
  Object.entries(replacements).forEach(([raw,label])=>{text=text.replaceAll(raw,label)});
  return text;
}

function headers(json=true){const value={"X-Employee-ID":$("employee").value,"X-Session-ID":$("session").value};if(authToken)value["Authorization"]=`Bearer ${authToken}`;if(json)value["Content-Type"]="application/json";return value}
async function api(path,options={}){
  const isForm=options.body instanceof FormData;
  const response=await fetch(path,{...options,headers:{...headers(!isForm),...(options.headers||{})}});
  const contentType=response.headers.get("content-type")||"";
  const data=contentType.includes("json")?await response.json():await response.text();
  ui.lastPayload=data;$("rawJson").textContent=JSON.stringify(data,null,2);
  if(!response.ok){const detail=data?.detail;const error=new Error(detail?.message||detail?.code||data?.message||`HTTP ${response.status}`);error.code=detail?.code||`HTTP_${response.status}`;error.detail=detail;throw error}
  return data;
}
function toast(message,tone="success"){const box=$("toast");box.className=`toast ${tone}`;box.innerHTML=message;clearTimeout(toast.timer);toast.timer=setTimeout(()=>box.classList.add("hidden"),5000)}
function setStage(step){
  ["stageInput","stageDocuments","stageProcessing","stageProfile","stageConfirmed"].forEach(id=>$(id).classList.add("hidden"));
  const map={1:"stageInput",2:"stageDocuments",3:"stageProcessing",4:"stageProfile",5:"stageConfirmed"};
  if(map[step])$(map[step]).classList.remove("hidden");
  const visibleStep=step===1?1:step===5?5:2;
  document.querySelectorAll("#stepper button").forEach(button=>{const n=Number(button.dataset.step);button.classList.toggle("active",n===visibleStep);button.classList.toggle("done",n<visibleStep)});
  const hints={1:"Nhập nhu cầu thật và tạo hồ sơ.",2:"Nạp hồ sơ doanh nghiệp; hệ thống kiểm tra định dạng và an toàn.",3:"Phân loại, trích xuất field và lưu nguồn.",4:"Đối chiếu dữ liệu và xác nhận hồ sơ.",5:"Hồ sơ đã xác nhận; sẵn sàng để Agent phân tích."};
  $("stageHint").textContent=hints[step]||hints[1];
}
function setIntakeStatus(status){ui.intakeStatus=status;const badge=$("intakeBadge");badge.textContent=status||"DRAFT";badge.className=`status-pill ${status==="profile_confirmed"?"green":status==="profile_review_required"?"amber":"neutral"}`;updateSummary()}
function updateSummary(){
  const status=ui.runtime?.status||ui.intakeStatus;
  $("summaryCase").textContent=ui.caseId||"Chưa tạo";
  $("summaryStatus").textContent=statusLabels[status]||status||"Chưa bắt đầu";
  $("summaryNext").textContent=nextCopy(status).title;
  const products=ui.runtime?.product_result?.recommendations?.map(x=>x.name||x.product_id)||[];
  $("summaryProducts").textContent=products.length?products.join(", "):"—";
  $("summaryAiLog").textContent=`${ui.runtime?.ai_decision_log?.length||0} bản ghi`;
}
function renderPendingFiles(){
  $("pendingFiles").innerHTML=ui.pendingFiles.map((file,index)=>`<div class="file-item"><span class="file-icon">${esc(file.name.split(".").pop().toUpperCase())}</span><div><strong>${esc(file.name)}</strong><small>${Math.ceil(file.size/1024)} KB · chờ tải lên</small></div><button class="icon-button remove-file" data-index="${index}">×</button></div>`).join("");
  document.querySelectorAll(".remove-file").forEach(button=>button.onclick=()=>{ui.pendingFiles.splice(Number(button.dataset.index),1);renderPendingFiles()});
}
function renderDocuments(){
  $("uploadedFiles").innerHTML=ui.documents.map(doc=>`<div class="file-item"><span class="file-icon">${esc(doc.filename.split(".").pop().toUpperCase())}</span><div><strong>${esc(doc.filename)}</strong><small>${esc(doc.document_type||"chưa phân loại")} · ${esc(doc.document_id)}</small></div><span class="file-state">${esc(doc.status)}</span></div>`).join("");
}
async function createCase(){
  const required=["companyName","taxCode","industry","needText"];
  const missing=required.find(id=>!$(id).value.trim());
  if(missing)return toast("Hãy nhập đủ doanh nghiệp, mã số thuế, ngành và nhu cầu khách hàng.","warning");
  try{
    resetRuntime();
    const data=await api("/api/v2/sales-cases",{method:"POST",headers:{"Idempotency-Key":`ui-${Date.now()}`},body:JSON.stringify({company_name:$("companyName").value,tax_code:$("taxCode").value,industry:$("industry").value,need_text:$("needText").value,rm_note:$("rmNote").value,priority:"normal",current_products:[]})});
    applyIntake(data);setStage(2);await loadCases();toast(`Đã tạo ${esc(ui.caseId)}. Hãy chọn hồ sơ doanh nghiệp để Agent xử lý.`);
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}. Không có action bên ngoài nào được thực hiện.`,"error")}
}

async function loadIntakeSuggestions(){
  const status=$("intakeAiStatus");
  if(!status)return;
  status.textContent="Đang tải dữ liệu CRM và chạy hai agent tư vấn...";
  try{
    const data=await api("/api/v2/sales-cases/intake-suggestions");
    const databaseFields=data.database_fields||{};
    Object.entries(databaseFields).forEach(([fieldId,value])=>{
      if($(fieldId))$(fieldId).value=value;
    });
    status.textContent=`Đã kế thừa ${Object.keys(databaseFields).length} trường từ ${data.source}.`;
    const products=data.product_suggestions||[];
    $("productAdviceList").innerHTML=products.length?`<ul>${products.map(product=>`
      <li><b>${esc(product.name)}</b>${product.requires_credit_verification?" · cần thẩm định tín dụng":""}<br>
      <small>${esc(product.reason)} Điều kiện: ${esc(product.eligibility_summary)}</small></li>`).join("")}</ul>`
      :'<p class="muted">Chưa có sản phẩm đủ căn cứ để gợi ý.</p>';
    const credit=data.credit_assessment||{};
    const creditTone=credit.status==="clear"?"success":credit.status==="warning"?"danger":"warning";
    $("creditAssessment").innerHTML=`
      <div class="notice ${creditTone}"><b>${esc(credit.conclusion||"Chưa thể kết luận")}</b></div>
      ${(credit.positive_signals||[]).length?`<p><b>Tín hiệu hiện có</b></p><ul>${credit.positive_signals.map(item=>`<li>${esc(item)}</li>`).join("")}</ul>`:""}
      <p><b>Cần Credit Agent xác minh</b></p>
      <ul>${(credit.missing_evidence||[]).map(item=>`<li>${esc(item)}</li>`).join("")}</ul>
      <div class="button-row" style="margin-top:10px">
        <button type="button" id="viewCreditHistory" class="button secondary">Xem chi tiết lịch sử tín dụng</button>
      </div>
      <div id="creditHistoryDetail" class="hidden" style="margin-top:10px"></div>`;
    const viewBtn=$("viewCreditHistory");
    if(viewBtn)viewBtn.onclick=()=>loadCicCreditHistory();
  }catch(error){
    status.textContent=`Không tải được gợi ý: ${error.message}`;
    $("productAdviceList").innerHTML='<p class="muted">Không có dữ liệu.</p>';
    $("creditAssessment").innerHTML='<p class="muted">Không có dữ liệu.</p>';
  }
}

async function loadCicCreditHistory(){
  const detail=$("creditHistoryDetail");
  const btn=$("viewCreditHistory");
  if(!detail)return;
  detail.classList.remove("hidden");
  detail.innerHTML='<p class="muted">Đang fetch CIC / lịch sử tín dụng...</p>';
  if(btn)btn.disabled=true;
  try{
    const data=await api("/api/v2/sales-cases/credit-history");
    const records=data.records||[];
    if(!records.length){
      detail.innerHTML=`<p class="muted">Không có bản ghi credit_history cho <b>${esc(data.customer_id)}</b>.</p>`;
      return;
    }
    const groupLabel=g=>`Nhóm ${g}`;
    const fmtVnd=n=>Number(n).toLocaleString("vi-VN")+" ₫";
    detail.innerHTML=`
      <div class="notice ${data.worst_cic_group>=2?"warning":"success"}">
        <b>${esc(data.customer_id)}</b> · ${records.length} khoản ·
        CIC xấu nhất: <b>${data.worst_cic_group!=null?groupLabel(data.worst_cic_group):"—"}</b>
      </div>
      <ul>${records.map(r=>`
        <li>
          <b>${esc(r.facility_type)}</b> · ${esc(r.lender)} · ${esc(r.source)}
          · ${groupLabel(r.cic_group)} · ${esc(r.status)}
          ${r.restructured?" · đã cơ cấu":""}
          <br><small>Dư nợ ${fmtVnd(r.outstanding_amount_vnd)} / gốc ${fmtVnd(r.original_amount_vnd)}
          · DPD max 12tháng: ${r.max_days_past_due_12m} ngày
          · Báo cáo ${esc(r.reported_at)}</small>
          ${r.note?`<br><small>${esc(r.note)}</small>`:""}
        </li>`).join("")}</ul>`;
  }catch(error){
    detail.innerHTML=`<p class="muted">Lỗi: ${esc(error.message)}</p>`;
  }finally{
    if(btn)btn.disabled=false;
  }
}
function resetRuntime(){ui.caseId=null;ui.intakeVersion=null;ui.stateVersion=null;ui.runtime=null;ui.profile=null;ui.conflicts=[];ui.documents=[];ui.pendingFiles=[];ui.approvalToken=null;ui.previewHash=null;$("resultsPanel").classList.add("hidden");renderControlLogs([],[],[])}
function applyIntake(data){ui.caseId=data.case_id;ui.intakeVersion=data.version;ui.intakeStatus=data.intake_status;ui.profile=data.profile;ui.conflicts=data.conflicts||[];setIntakeStatus(data.intake_status);if(data.profile)renderProfile(data.profile,ui.conflicts);updateSummary()}
async function uploadDocuments(){
  if(!ui.caseId)return toast("Hãy tạo case trước.","error");if(!ui.pendingFiles.length)return toast("Chưa có file chờ tải lên.","warning");
  try{const form=new FormData();ui.pendingFiles.forEach(file=>form.append("files",file));const data=await api(`/api/v2/sales-cases/${ui.caseId}/documents`,{method:"POST",body:form});applyIntake(data);ui.pendingFiles=[];renderPendingFiles();await loadDocuments();setStage(3);toast("File đã qua kiểm tra định dạng, hash và prompt-injection. Sẵn sàng trích xuất.")}
  catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}
async function loadDocuments(){if(!ui.caseId)return;try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/documents`);ui.documents=data.documents||[];renderDocuments()}catch(error){toast(esc(error.message),"error")}}
async function processDocuments(){
  const spinner=document.querySelector(".spinner");spinner.classList.add("running");$("processDocuments").disabled=true;
  try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/process-documents`,{method:"POST"});applyIntake(data);await loadDocuments();renderJobs(data.processing?.jobs||[]);setStage(4);toast(`Đã trích xuất ${data.profile?Object.keys(data.profile.source_map||{}).length:0} trường kèm nguồn. RM cần xác nhận.`)}
  catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
  finally{spinner.classList.remove("running");$("processDocuments").disabled=false}
}
function renderJobs(jobs){$("processingJobs").innerHTML=jobs.map(job=>`<div class="job"><span>${esc(job.document_id)} · ${esc(job.stage)}</span><b>${esc(job.status)}</b></div>`).join("")}
function renderProfile(profile,conflicts=[]){
  ui.profile=profile;ui.conflicts=conflicts;
  const unresolved=conflicts.filter(x=>x.requires_confirmation);
  $("conflictList").innerHTML=unresolved.map((item,ci)=>`<div class="conflict"><h3>⚠ Xung đột: ${esc(item.field_name)}</h3><p class="muted">Trường ảnh hưởng quyết định. Chọn giá trị RM đã đối chiếu:</p><div class="candidate-list">${item.candidates.map((candidate,vi)=>`<button class="candidate conflict-choice" data-ci="${ci}" data-vi="${vi}"><b>${esc(pretty(candidate.value))}</b><br><small>${esc(candidate.source_id)} · ${Math.round((candidate.confidence||0)*100)}%</small></button>`).join("")}</div></div>`).join("")||'<div class="notice success">Không còn xung đột high-impact chưa xử lý.</div>';
  document.querySelectorAll(".conflict-choice").forEach(button=>button.onclick=()=>{const item=unresolved[Number(button.dataset.ci)];const candidate=item.candidates[Number(button.dataset.vi)];patchProfile(item.field_name,candidate.value,"RM chọn nguồn sau khi đối chiếu xung đột")});
  const sections=Object.keys(profileLabels).map(key=>{const values=profile[key]||{};const rows=Object.entries(values);if(!rows.length)return "";return `<div class="profile-section"><h3>${esc(profileLabels[key])}</h3>${rows.map(([name,value])=>{const path=`${key}.${name}`;return `<div class="profile-field"><span>${esc(name.replaceAll("_"," "))}<em class="source-chip">${esc(profile.source_map?.[path]||"—")}</em></span><b>${esc(pretty(value))}</b></div>`}).join("")}</div>`}).join("");
  const needs=`<div class="profile-section"><h3>Nhu cầu & pain point</h3><div class="profile-field"><span>explicit needs</span><b>${esc((profile.explicit_needs||[]).join(", ")||"—")}</b></div><div class="profile-field"><span>pain points</span><b>${esc((profile.pain_points||[]).join("; ")||"—")}</b></div></div>`;
  $("profileView").innerHTML=sections+needs;
  $("snapshotHash").textContent=profile.snapshot_hash||"—";
}
function parseCorrection(field,value){if(["business_profile.employees_count","business_profile.annual_revenue","business_profile.account_or_unit_count"].includes(field))return Number(value);if(field==="explicit_needs")return value.split(",").map(x=>x.trim()).filter(Boolean);return value}
async function patchProfile(field,value,reason="RM chỉnh sửa tại Workspace"){
  if(value===""||value===null||Number.isNaN(value))return toast("Giá trị chỉnh sửa không hợp lệ.","error");
  try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/extracted-profile`,{method:"PATCH",body:JSON.stringify({expected_version:ui.intakeVersion,changes:[{field_name:field,value,reason}]})});applyIntake(data);toast(`Đã lưu ${esc(field)} với provenance RM_CONFIRMATION.`)}catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}
async function confirmProfile(){
  if(!$("attestation").checked)return toast("RM cần tích xác nhận đã đối chiếu hồ sơ.","warning");
  try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/confirm-profile`,{method:"POST",body:JSON.stringify({expected_version:ui.intakeVersion,attestation:true})});applyIntake(data);setStage(5);toast("Customer Business Snapshot đã được xác nhận và khóa hash.")}
  catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}
async function runAnalysis(){
  $("runAnalysis").disabled=true;$("runAnalysis").textContent="Đang chạy Product + Credit + Insurance Experts…";
  try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/run-analysis`,{method:"POST",body:JSON.stringify({expected_version:ui.intakeVersion})});ui.intakeVersion=data.intake_version;ui.stateVersion=data.state_version;ui.runtime=data.case;renderRuntime(data.case);await loadControlLogs();await loadCases();toast(`Phân tích hoàn tất an toàn: ${esc(statusLabels[data.case.status]||data.case.status)}.`)}
  catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
  finally{$("runAnalysis").disabled=false;$("runAnalysis").textContent="Chạy lại phân tích end-to-end →"}
}
async function loadSpecialistReviews(caseId) {
  try {
    const list = await api(`/api/v2/cases/${caseId}/specialist-reviews`);
    const container = $("specialistReviewsList");
    if (!list || !list.length) {
      container.innerHTML = '<p class="muted" style="margin:0;">Chưa có ý kiến chuyên viên.</p>';
      return;
    }
    container.innerHTML = list.map(item => `
      <div style="margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--line); font-size:12.5px;">
        <span class="status-pill ${item.decision === "cleared" ? "green" : (item.decision === "blocked" ? "red" : "amber")}" style="float:right; font-size:8px;">
          ${item.decision.toUpperCase()}
        </span>
        <b>${esc(item.review_type.toUpperCase().replaceAll("_", " "))}</b>
        <span class="muted" style="font-size:10px;"> · bởi ${esc(item.reviewer_employee_id)} lúc ${esc(new Date(item.created_at).toLocaleString("vi-VN"))}</span>
        <p style="margin:6px 0 0 0; font-size:12.5px;"><b>Ý kiến:</b> ${esc(item.summary)}</p>
        ${(item.findings || []).length ? `<p style="margin:2px 0 0 0; font-size:11px; color:var(--muted);"><b>Findings:</b> ${item.findings.join("; ")}</p>` : ""}
      </div>
    `).join("");
  } catch (err) {
    console.warn("Could not load specialist reviews", err);
  }
}

function renderRuntime(state){ui.runtime=state;ui.stateVersion=ui.stateVersion||state.state_version;$("resultsPanel").classList.remove("hidden");renderDecisionOverview(state);renderIntent(state.intent_result);renderProducts(state.product_result);renderEligibility(state.eligibility_result);renderExpertResults(state);renderCoordinator(state);renderPlan(state.execution_plan);renderOperations(state.operations_result);renderNextAction(state);renderEvidence(state.evidences||[]);renderAiLog(state.ai_decision_log||[]);updateSummary();loadSpecialistReviews(state.case_id);document.querySelector("#resultsPanel").scrollIntoView({behavior:"smooth",block:"start"})}
function renderIntent(intent){if(!intent)return $("intentResult").innerHTML='<p class="muted">Chưa đủ dữ liệu để kết luận.</p>';const intents=[intent.primary_intent,...(intent.sub_intents||[])];$("intentResult").innerHTML=`<div class="primary-insight">${esc(intent.user_goal)}</div><div class="chips">${intents.map(x=>`<span class="chip">${esc(intentLabels[x]||x)}</span>`).join("")}</div><p class="muted">Độ tin cậy: <b>${Math.round((intent.overall_confidence||0)*100)}%</b><br>Hành vi: ${esc(intent.recommended_action)}</p>`}
const baselineMapping = {
  "payroll_premium": "Payroll Premium Package",
  "cash_management_sme": "SME Cash Management Bundle",
  "working_capital_unsecured": "Working Capital Unsecured Loan",
  "bulk_payment_api": "Bulk Payment API Integration"
};
function renderProducts(result){const items=result?.recommendations||[];$("productResult").innerHTML=items.length?items.map(item=>`<div class="product-card"><strong>${esc(item.name || baselineMapping[item.product_id] || item.product_id)}</strong><span class="score">Match ${Math.round((item.match_score||0)*100)}/100</span><p>${esc(item.matching_reason)}</p><span class="chip blue">${esc(item.product_id)}</span></div>`).join(""):'<p class="muted">Không có sản phẩm đủ grounded. Hệ thống không tự bịa catalog.</p>'}
function renderEligibility(result){const items=result?.products||[];const label={passed:"Đạt rule",pending_information:"Thiếu dữ liệu",pending_review:"Cần review",failed:"Không đạt"};$("eligibilityResult").innerHTML=items.length?items.map(product=>`<div class="eligibility-card"><b>${esc(baselineMapping[product.product_id] || product.product_id)} · ${esc(label[product.status]||product.status)}</b>${(product.rules||[]).map(rule=>{const tone=rule.status==="passed"?"pass":rule.status==="failed"?"fail":"wait";return `<div class="rule ${tone}"><i>${tone==="pass"?"✓":tone==="fail"?"×":"!"}</i><span>${esc(rule.rule_id)}<br><small>${esc(label[rule.status]||rule.status)}</small></span></div>`}).join("")}</div>`).join(""):'<p class="muted">Chưa chạy điều kiện vì intent hoặc sản phẩm chưa rõ.</p>'}
function expertFinding(state, agentType){return (state.expert_findings||[]).find(item=>item.agent_type===agentType)}
function agentMeta(finding,status){if(!finding)return "";const run=finding.agent_run||{};const notApplicable=status==="not_applicable";const confidence=notApplicable?"Đã xác định phạm vi":`${Math.round((finding.confidence?.display_confidence||0)*100)}% tin cậy`;const tools=(run.tools_called||[]).map(item=>toolLabels[item]||item);return `<div class="expert-meta"><span class="chip">${esc(modeLabels[run.mode]||run.mode||"Không rõ chế độ")}</span><span class="chip blue">${(finding.evidence_refs||[]).length} nguồn</span><span class="chip">${esc(confidence)}</span></div><small class="muted">Nguồn xử lý: ${esc(tools.join(", ")||"Không cần gọi nguồn ngoài")}</small>`}
function listItems(items, emptyText){return items?.length?`<ul class="expert-facts">${items.slice(0,5).map(item=>{const raw=typeof item==="string"?item:(item.display_name||item.name||item.title||item.reason||item.code||item.field||item.requirement||item.description||JSON.stringify(item));return `<li>${esc(readableField(raw))}</li>`}).join("")}</ul>`:`<p class="muted">${esc(emptyText)}</p>`}
function renderDecisionOverview(state){
  const synthesis=state.synthesis_result||{};const primary=synthesis.primary_solution;const products=state.eligibility_result?.products||[];const statuses=products.map(x=>x.status);const missing=synthesis.missing_information||[];const next=nextCopy(state.status);
  $("decisionHeadline").textContent=primary?.name||primary?.product_name||primary?.product_id||"Chưa có phương án đủ căn cứ";
  $("decisionReason").textContent=primary?.matching_reason||"Coordinator chưa chọn phương án chính vì context hoặc bằng chứng chưa đủ.";
  $("decisionEligibility").textContent=statuses.some(x=>x==="failed"||x==="pending_review")?"Có điều kiện chặn":statuses.some(x=>x==="pending_information")?"Cần bổ sung dữ liệu":statuses.length?"Đạt kiểm tra sơ bộ":"Chưa kiểm tra";
  $("decisionMissing").textContent=missing.length?`${missing.length} mục cần xử lý`:"Không có mục chặn";
  $("decisionNext").textContent=next.title;
}
function renderExpertResults(state){
  const productFinding=expertFinding(state,"ProductExpert");
  const creditFinding=expertFinding(state,"CreditExpert");
  const insuranceFinding=expertFinding(state,"InsuranceExpert");
  const productCount=state.product_result?.recommendations?.length||0;
  $("productExpertOutput").innerHTML=productFinding?`<p><b>Kết luận:</b> ${esc(productFinding.conclusion)}</p><p>${productCount} sản phẩm được xếp hạng có nguồn.</p>${agentMeta(productFinding,state.product_result?.status)}`:'<p class="muted">Product Expert chưa chạy hoặc case chỉ dùng luồng tra cứu đơn giản.</p>';
  const credit=state.credit_result;
  $("creditExpertOutput").closest("article").classList.toggle("not-applicable",credit?.status==="not_applicable");
  $("creditExpertOutput").innerHTML=credit?`<span class="plain-status">${esc(domainStatusLabels[credit.status]||credit.status)}</span><p>${esc(credit.conclusion)}</p>${credit.status!=="not_applicable"?`<b>Thông tin còn thiếu</b>${listItems(credit.missing_information,"Không có trường thiếu được ghi nhận.")}<b>Điều kiện chặn</b>${listItems(credit.hard_blocks,"Không phát hiện điều kiện chặn tín dụng.")}`:""}${agentMeta(creditFinding,credit.status)}`:'<p class="muted">Case hiện chưa có kết quả Credit Expert.</p>';
  const insurance=state.insurance_result;
  $("insuranceExpertOutput").closest("article").classList.toggle("not-applicable",insurance?.status==="not_applicable");
  $("insuranceExpertOutput").innerHTML=insurance?`<span class="plain-status">${esc(domainStatusLabels[insurance.status]||insurance.status)}</span><p>${esc(insurance.conclusion)}</p>${insurance.status!=="not_applicable"?`<b>Yêu cầu bảo hiểm</b>${listItems(insurance.coverage_checks,"Không có yêu cầu bảo hiểm áp dụng cho phương án hiện tại.")}<b>Thông tin còn thiếu</b>${listItems(insurance.missing_information,"Không có trường thiếu được ghi nhận.")}`:""}${agentMeta(insuranceFinding,insurance.status)}`:'<p class="muted">Case hiện chưa có kết quả Insurance Expert.</p>';
  const session=state.collaboration_session;
  const badge=$("collaborationStatus");
  badge.textContent=session?.status?.toUpperCase()||"CHƯA CHẠY";
  badge.className=`status-pill ${session?.status==="converged"?"green":session?"amber":"neutral"}`;
}
function renderCoordinator(state){
  const synthesis=state.synthesis_result;
  if(!synthesis)return $("coordinatorResult").innerHTML='<p class="muted">Coordinator chưa tổng hợp vì workflow chưa chạy đủ ba Expert.</p>';
  const primary=synthesis.primary_solution;
  const missing=synthesis.missing_information||[];
  const reviews=synthesis.human_review_requirements||[];
  const alternatives=synthesis.alternative_solutions||[];
  $("coordinatorResult").innerHTML=`<div class="coordinator-summary"><div><h3>Phương án chính</h3>${primary?`<p><b>${esc(primary.name||primary.product_name||primary.product_id||"Phương án được chọn")}</b></p><p>${esc(primary.matching_reason||primary.reason||"Được tổng hợp từ các finding đã kiểm chứng.")}</p>`:'<p class="muted">Chưa chọn phương án chính.</p>'}${alternatives.length?`<h3>Giải pháp bổ trợ</h3><ul class="expert-facts">${alternatives.map(item=>`<li><b>${esc(item.name||item.product_id)}</b> — ${esc(item.matching_reason||"")}</li>`).join("")}</ul>`:""}<p>Ứng viên bị chặn: <b>${(synthesis.blocked_candidates||[]).length}</b></p></div><div><h3>Điểm RM cần xử lý</h3>${listItems(missing.map(x=>x.field||x),"Không có thông tin thiếu ở bước tổng hợp.")}${reviews.length?`<h3>Yêu cầu rà soát</h3><ul class="expert-facts">${reviews.map(item=>`<li><b>${esc(item.role||"Chuyên viên")}</b>: ${esc(item.reason||"")}</li>`).join("")}</ul>`:'<p class="muted">Không có yêu cầu rà soát bổ sung.</p>'}<p class="muted">Tổng hợp từ ${(synthesis.source_finding_ids||[]).length} kết quả chuyên gia · Policy ${esc(synthesis.synthesis_policy_version)}</p></div></div>`;
}
function renderPlan(plan){$("planVersion").textContent=plan?`v${plan.plan_version}`:"v—";$("executionPlan").innerHTML=plan?.steps?.map(step=>`<div class="plan-step ${esc(step.status)}"><b>${esc(step.title)}</b><span>${esc(step.owner)} · ${esc(step.status)}</span><small>${esc(step.reason||step.stop_condition||"")}</small></div>`).join("")||'<p class="muted">Planner chưa tạo kế hoạch vì nhu cầu cần làm rõ.</p>'}
function renderOperations(op){if(!op)return $("operationsResult").innerHTML='<p class="muted">Chưa tạo operations draft.</p>';const checklist=op.required_document_checklist||[];$("operationsResult").innerHTML=`<div class="operations-grid"><div class="op-block"><h3>Checklist hồ sơ</h3>${checklist.map(item=>`<div class="check-item"><i>${item.current_status==="verified"?"✓":"!"}</i><span>${esc(item.display_name)}<br><small>${esc((item.source_rule_ids||[]).join(", ")||"product prerequisite")}</small></span><b>${item.current_status==="verified"?"Đã có":"Còn thiếu"}</b></div>`).join("")||'<p class="muted">Không có hồ sơ bổ sung.</p>'}</div><div class="op-block"><h3>Đề xuất nháp · chưa gửi</h3><div class="draft-box"><b>${esc(op.proposal_draft?.title||"")}</b>\n\n${(op.proposal_draft?.solutions||[]).map(x=>`• ${x.name}: ${x.matching_reason}`).join("\n")}\n\n${esc(op.proposal_draft?.disclaimer||"")}</div></div><div class="op-block"><h3>Phản hồi khách hàng · chưa gửi</h3><div class="draft-box">${esc(op.customer_message_draft?.body||"")}</div></div><div class="op-block"><h3>Action draft</h3><div class="draft-box">${esc(JSON.stringify(op.action_payload||{},null,2))}</div></div></div>`}
function nextCopy(status){const map={draft:["Nạp hồ sơ","Tải lên tài liệu để hệ thống có nguồn."],files_uploaded:["Đọc hồ sơ","Chạy phân loại và trích xuất."],profile_review_required:["RM xác nhận context","Xử lý xung đột rồi xác nhận snapshot."],profile_confirmed:["Chạy phân tích","Tìm sản phẩm và kiểm tra rule."],clarification_required:["Làm rõ nhu cầu","Nêu mục tiêu, pain point và kết quả mong muốn."],pending_information:["Bổ sung hồ sơ còn thiếu","Chỉ resume phần bị ảnh hưởng sau khi có evidence."],pending_review:["Chuyển chuyên viên kiểm tra","Không cho tự phê duyệt khi evidence/rule chưa an toàn."],pending_approval:["Kiểm tra và phê duyệt payload","RM duyệt hành động, không phải duyệt cấp sản phẩm."],completed:["Hoàn tất phân tích","Xem AI log và lịch sử audit để kiểm tra."],rejected:["Case đã dừng","Tạo case mới nếu cần."]};const value=map[status]||["Tiếp tục theo workflow","Xem bước đang được tô đỏ."];return {title:value[0],reason:value[1]}}
function riskGateBanner(riskGateResult){if(!riskGateResult||riskGateResult.risk_level!=="high")return"";const reasonLabels={eligibility_hard_block:"Vi phạm điều kiện bắt buộc (không thể tự bổ sung hồ sơ để qua)",eligibility_policy_conflict_or_live_check_unavailable:"Xung đột chính sách hoặc không xác minh được nguồn sống (PEP/AML/watchlist)",unsupported_evidence_claim:"Evidence Validator phát hiện trích dẫn không khớp nguồn — nghi ngờ ảo giác",unrecognized_eligibility_status:"Trạng thái thẩm định không xác định — chặn theo nguyên tắc fail-closed"};const reasons=(riskGateResult.reasons||[]).map(r=>reasonLabels[r]||r);return `<div class="notice danger"><b>⚠ Rủi ro cao — bắt buộc chuyên viên/compliance review, không tự động phê duyệt</b><br>${reasons.map(esc).join("; ")}${riskGateResult.triggered_rules?.length?`<br><small>Rule/claim liên quan: ${riskGateResult.triggered_rules.map(esc).join(", ")}</small>`:""}</div>`}
function renderNextAction(state){const copy=nextCopy(state.status);const questions=state.next_best_questions||[];const actions=state.next_best_actions||[];$("nextAction").innerHTML=`${riskGateBanner(state.risk_gate_result)}<div class="next-title">${esc(copy.title)}</div><p class="next-reason">${esc(copy.reason)}</p>${questions.slice(0,3).map(q=>`<div class="question-card"><b>Cần hỏi:</b> ${esc(humanizeText(q.question))}<br><small>${esc(humanizeText(q.reason))}</small></div>`).join("")}${actions.slice(0,3).map(a=>`<div class="action-card"><b>${esc(humanizeText(a.title))}</b><br><small>${esc(humanizeText(a.rationale))}</small></div>`).join("")}`;renderActionButtons(state.status)}
function renderActionButtons(status){
  let html="";
  if(status==="pending_information")html='<button id="supplementDocs" class="button primary">Bổ sung hồ sơ còn thiếu</button>';
  if(status==="pending_approval")html='<button id="approveAndExecute" class="button primary">Duyệt payload & thực thi CRM</button>';
  if(status==="clarification_required")html='<button id="editNeed" class="button primary">Sửa và tạo case mới</button>';
  if(status==="pending_review")html='<button id="rejectCase" class="button ghost" style="color:var(--danger)">Từ chối case này</button>';
  $("actionButtons").innerHTML=html;
  if($("supplementDocs"))$("supplementDocs").onclick=()=>{setStage(2);$("intakePanel").scrollIntoView({behavior:"smooth"})};
  if($("approveAndExecute"))$("approveAndExecute").onclick=approveAndExecute;
  if($("editNeed"))$("editNeed").onclick=()=>{setStage(1);$("intakePanel").scrollIntoView({behavior:"smooth"})};
  if($("rejectCase"))$("rejectCase").onclick=rejectCase;
}

async function rejectCase(){
  if(!confirm("Xác nhận từ chối case này? Hành động không thể hoàn tác."))return;
  try{
    const data=await api(`/api/v2/sales-cases/${ui.caseId}/reject`,{method:"POST",body:JSON.stringify({reason:"RM từ chối tại Workspace sau khi xem xét kết quả rule."})});
    applyIntake(data);
    toast("Case đã bị từ chối và ghi vào audit log.","warning");
    await loadCases();
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,'error')}
}
function renderEvidence(items){$("evidenceList").innerHTML=items.map(item=>`<div class="evidence"><b>${esc(item.claim)}</b><span>${esc(item.source_document_id)} · ${esc(item.source_version)}</span><small>${esc(item.location)} · validation ${Math.round((item.validation_score||0)*100)}%</small></div>`).join("")||'<p class="muted">Chưa có nguồn.</p>'}
function renderAiLog(entries){$("summaryAiLog").textContent=`${entries.length} bản ghi`;$("aiLog").innerHTML=entries.map(item=>`<div class="log-entry"><b>${esc(item.component)} · ${esc(item.event)}</b><span>${esc(item.mode)} · ${esc(item.model)} · ${item.latency_ms||0} ms</span><small>${esc(item.prompt_or_policy_version)} · ${item.sources?.length||0} nguồn · ${item.token_usage?.total||0} token</small></div>`).join("")||'<p class="muted">Chưa có AI log.</p>'}
function renderAudit(events,valid){$("auditLog").innerHTML=`<div class="notice ${valid?"success":"danger"}">Hash-chain: <b>${valid?"HỢP LỆ":"KHÔNG HỢP LỆ"}</b></div>`+events.map(item=>`<div class="log-entry"><b>${esc(item.action)}</b><span>${esc(item.actor)} · ${esc(item.created_at||item.at)}</span><small>${esc(item.event_hash||"")}</small></div>`).join("")}
function renderControlLogs(evidence,ai,audit){renderEvidence(evidence);renderAiLog(ai);renderAudit(audit,true)}
async function loadControlLogs(){if(!ui.caseId||!ui.runtime)return;try{const [ai,audit]=await Promise.all([api(`/api/v2/sales-cases/${ui.caseId}/ai-log`),api(`/api/v2/sales-cases/${ui.caseId}/audit`)]);renderAiLog(ai.entries||[]);renderAudit(audit.events||[],audit.chain_valid)}catch(error){toast(`Không tải được log: ${esc(error.message)}`,"error")}}
async function previewApproval(){try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/approval-preview`,{method:"POST"});ui.previewHash=data.payload_hash;$("actionButtons").insertAdjacentHTML("beforeend",`<div class="approval-preview"><b>Payload hash</b><small>${esc(data.payload_hash)}</small><pre>${esc(JSON.stringify(data.payload,null,2))}</pre></div>`);toast("Đã hiển thị đúng payload được khóa cho approval.","warning")}catch(error){toast(esc(error.message),"error")}}
async function approveAndExecute(){
  const btn=$("approveAndExecute");
  if(btn)btn.disabled=true;
  try{
    if(!ui.previewHash)await previewApproval();
    const data=await api(`/api/v2/sales-cases/${ui.caseId}/approve`,{method:"POST",body:JSON.stringify({expected_state_version:ui.stateVersion,payload_hash:ui.previewHash})});
    ui.approvalToken=data.approval_token;ui.stateVersion=data.state_version;
    // Log accepted feedback for personalization learning
    await logPersonalizationFeedback("accepted");
    await executeAction();
  }catch(error){
    if(btn)btn.disabled=false;
    toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error");
  }
}
async function executeAction(){try{const data=await api(`/api/v2/sales-cases/${ui.caseId}/execute-actions`,{method:"POST",headers:{"X-Approval-Token":ui.approvalToken},body:JSON.stringify({idempotency_key:`${ui.caseId}:ui-execute-v1`,expected_state_version:ui.stateVersion})});ui.stateVersion=data.state_version;const latest=await api(`/api/v2/cases/${ui.caseId}`);ui.runtime=latest.case;renderRuntime(latest.case);await loadControlLogs();toast(`Đã tạo opportunity ${esc(data.result.opportunity_id)} và các task đồng bộ trên hệ thống CRM.`)}catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}}
async function loadCases(){
  try{
    const items=await api("/api/v2/sales-cases");
    $("caseList").innerHTML=items.length?items.map(item=>{
      const customerSubmitted=item.manual_input?.submission_source==="customer";
      return `<button class="case-item" data-case="${esc(item.case_id)}"><strong>${esc(item.manual_input?.company_name||item.case_id)}</strong><span>${esc(item.case_id)} · ${esc(statusLabels[item.runtime_status||item.intake_status]||item.runtime_status||item.intake_status)}</span>${customerSubmitted?'<small class="plain-status">Khách hàng vừa gửi</small>':""}</button>`;
    }).join(""):'<p class="muted">Chưa có case.</p>';
    document.querySelectorAll(".case-item").forEach(button=>button.onclick=()=>openCase(button.dataset.case));
  }catch(error){toast(`Không tải được danh sách case: ${esc(error.message)}`,"error")}
}
async function openCase(caseId){try{const items=await api("/api/v2/sales-cases");const item=items.find(x=>x.case_id===caseId);if(!item)return;resetRuntime();applyIntake(item);await loadDocuments();if(item.runtime_status){const runtime=await api(`/api/v2/cases/${caseId}`);ui.stateVersion=runtime.state_version;renderRuntime(runtime.case);await loadControlLogs();setStage(5)}else if(item.intake_status==="profile_review_required")setStage(4);else if(item.intake_status==="profile_confirmed")setStage(5);else if(item.intake_status==="files_uploaded")setStage(3);else setStage(2);toast(`Đã mở lại ${esc(caseId)} từ PostgreSQL.`)}catch(error){toast(esc(error.message),"error")}}

// =====================================================================
// NEW ROLE-AWARE & WORK OPTIMIZATION COGNITIVE LAYER INTEGRATION
// =====================================================================

async function loadEmployeeContext() {
  let empId = $("employee").value;

  // FAIL-CLOSED: Simulate error conditions
  if (empId === "EXPIRED_TOKEN" || empId === "IAM_ERROR") {
    handleFailClosed(empId);
    return;
  }

  try {
    const data = await api("/api/v2/me/context");

    // The session token is the identity source of truth. A stale token from a
    // previous login must not run under the dropdown's default employee.
    if (data.employee_id && data.employee_id !== empId) {
      empId = data.employee_id;
      $("employee").value = empId;
    }

    // Route by role FIRST so the correct workspace shows immediately;
    // personalization/habits are cosmetic and can hydrate afterwards.
    const role = data.authorization_context?.roles?.[0];
    routeWorkspace(role);

    const roleLabel = { customer_user:"Người dùng", relationship_manager:"Nhân viên giao dịch", legal_specialist:"Legal/Compliance Reviewer", product_specialist:"Product Specialist", credit_specialist:"Chuyên viên thẩm định", insurance_specialist:"Insurance Specialist", manager:"Người phê duyệt cuối" }[role] || role;
    $("roleBadge").textContent = `Role: ${roleLabel}`;
    if($("heroRole"))$("heroRole").textContent = `Role hiện tại: ${roleLabel} (${empId})`;
    toast(`SSO <b>${esc(empId)}</b> · Role: <b>${esc(roleLabel)}</b>`);

    // Apply personalization from server
    const pCtx = data.personalization_context;
    if (pCtx) {
      $("togglePersonalization").checked = pCtx.enabled;
      if (pCtx.preferences?.default_case_view) {
        $("prefDefaultTab").value = pCtx.preferences.default_case_view;
        const tabBtn = $("tabButton" + pCtx.preferences.default_case_view.charAt(0).toUpperCase() + pCtx.preferences.default_case_view.slice(1));
        if (tabBtn) tabBtn.click();
      }
      if (pCtx.preferences?.preferred_email_template)
        $("prefEmailTemplate").value = pCtx.preferences.preferred_email_template;
    }

    // Load habits in the background (if panel exists)
    loadHabits();
  } catch (error) {
    hideAllWorkspaces();
    if (error.status === 401 || error.message.includes("401")) {
      toast(`<b>401 Unauthenticated:</b> SSO Token không hợp lệ.`, "error");
    } else if (error.status === 403 || error.message.includes("403")) {
      toast(`<b>403 Forbidden:</b> Nhân viên không được cấp quyền truy cập.`, "error");
    } else if (error.status === 503 || error.message.includes("503")) {
      toast(`<b>503 IAM Unavailable:</b> Cổng xác thực mất kết nối. Chặn toàn bộ truy cập.`, "error");
    } else {
      toast(`Lỗi xác thực: ${esc(error.message)}`, "error");
    }
  }
}

function handleFailClosed(type) {
  hideAllWorkspaces();
  if (type === "EXPIRED_TOKEN") {
    toast("<b>401 Unauthenticated:</b> Phiên làm việc hết hạn. SSO Token Verification Failed. Vui lòng đăng nhập lại.", "error");
  } else if (type === "IAM_ERROR") {
    toast("<b>503 Service Unavailable:</b> Cổng IAM của SHB đang bảo trì hoặc mất kết nối. Chặn toàn bộ quyền truy cập dữ liệu để đảm bảo an toàn.", "error");
  }
}

function hideAllWorkspaces() {
  $("rmWorkspace").classList.add("hidden");
  $("customerWorkspace").classList.add("hidden");
  $("specialistWorkspace").classList.add("hidden");
  $("managerWorkspace").classList.add("hidden");
  $("personalizationPanel").classList.add("hidden");
  const hw = $("habitsPanelWrapper"); if(hw) hw.classList.add("hidden");
}

function routeWorkspace(role) {
  hideAllWorkspaces();

  if (role === "customer_user") {
    $("customerWorkspace").classList.remove("hidden");
    $("workspaceTitle").textContent = "Cổng thông tin khách hàng · Chỉ nhập dữ liệu";
    const customerId = loginCustomerId();
    ensureCustomerSessionOption(customerId, sessionStorage.getItem("shb_company_name") || customerId);
    $("session").value = "SESS-" + customerId.replace("COMP-", "");
    $("session").disabled = true;
    loadCustomerProfile();
    loadCustomerCases();
    loadCustomerCreditRequests();
  } else if (role === "relationship_manager") {
    $("personalizationPanel").classList.remove("hidden");
    $("session").disabled = false;
    $("rmWorkspace").classList.remove("hidden");
    $("workspaceTitle").textContent = "RM Workspace · Personalization Active";
    loadNextBestWorkQueue();
    loadRmCreditForwardQueue();
    loadIntakeSuggestions();
  } else if (role.endsWith("_specialist")) {
    $("personalizationPanel").classList.remove("hidden");
    $("session").disabled = false;
    $("specialistWorkspace").classList.remove("hidden");
    $("workspaceTitle").textContent = `${role.toUpperCase().replaceAll("_", " ")} Workspace`;
    loadSpecialistQueue();
    if(role==="credit_specialist")loadCreditApprovalRequests();
    else $("creditApprovalPanel").classList.add("hidden");
    loadAgentKnowledgeConsole();
    loadCreditHistory();
  } else if (role === "manager") {
    $("personalizationPanel").classList.remove("hidden");
    $("session").disabled = false;
    $("managerWorkspace").classList.remove("hidden");
    $("workspaceTitle").textContent = "Manager Console · Phê duyệt cuối";
    loadManagerWorkload();
    loadManagerApprovalRequests();
  }
}

function resolveLoginEmployeeId() {
  const role = $("loginRole")?.value;
  if (role === "customer") return $("loginCustomerUser")?.value || "USER-MP-001";
  if (role === "staff") return "RM-999"; // merged persona: intake + appraisal
  if (role === "manager") return "MGR-HN-01";
  return "RM-999";
}

async function login(event) {
  event.preventDefault();
  $("loginError").textContent = "";
  try {
    const employeeId = resolveLoginEmployeeId();
    if ($("loginRole")?.value === "customer") {
      const opt = $("loginCustomerUser")?.selectedOptions?.[0];
      sessionStorage.setItem("shb_customer_id", opt?.dataset?.customerId || "COMP-MP");
      sessionStorage.setItem("shb_company_name", opt?.textContent?.split(" · ")[0] || "");
    }
    const response = await fetch("/api/v2/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({employee_id:employeeId, password:$("loginPassword").value})});
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message || "Đăng nhập thất bại.");
    authToken = data.access_token;
    sessionStorage.setItem("shb_access_token", authToken);
    if (![...$("employee").options].some(option => option.value === data.employee_id)) {
      $("employee").add(new Option(data.employee_id, data.employee_id));
    }
    $("employee").value = data.employee_id;
    $("employee").disabled = true;
    // Ẩn mọi workspace ngay lập tức: rmWorkspace là khối mặc định trong HTML,
    // nếu không ẩn sẽ lộ UI RM trong lúc chờ context trả về.
    hideAllWorkspaces();
    $("loginScreen").style.display = "none";
    // Route theo role trước (nhanh), case list tải nền sau.
    await loadEmployeeContext();
    loadCases();
  } catch (error) {
    $("loginError").textContent = error.message;
  }
}

function loginCustomerId() {
  return sessionStorage.getItem("shb_customer_id") || "COMP-MP";
}

function ensureCustomerSessionOption(customerId, companyName) {
  const value = "SESS-" + customerId.replace("COMP-", "");
  if (![...$("session").options].some(option => option.value === value)) {
    $("session").add(new Option(`${companyName} · ${customerId}`, value));
  }
}

async function loadCustomerProfile() {
  try {
    const data = await api("/api/v2/context/current");
    const attributes = data.context?.customer?.attributes || {};
    const fields = {
      customerCompanyName: attributes.company_name || attributes.name,
      customerTaxCode: attributes.tax_code,
      customerIndustry: attributes.industry,
      customerContact: attributes.contact,
      customerEmployees: attributes.employees_count,
      customerRevenue: attributes.annual_revenue,
      customerOperatingYears: attributes.operating_years,
    };
    Object.entries(fields).forEach(([id, value]) => {
      $(id).value = value ?? "";
    });
    const companyName = attributes.company_name || attributes.name;
    if (companyName) $("customerProfileTitle").textContent = `Phiếu nhu cầu ${companyName}`;
  } catch (error) {
    toast(`Không tự điền được hồ sơ doanh nghiệp: ${esc(error.message)}`, "warning");
  }
}

async function loadSessionCompanies() {
  const select = $("session");
  if (!select) return;
  try {
    const response = await fetch("/api/v2/auth/companies");
    const companies = await response.json();
    if (!Array.isArray(companies) || !companies.length) return; // keep static fallback
    const current = select.value;
    select.innerHTML = companies.map(c =>
      `<option value="SESS-${esc(String(c.customer_id).replace("COMP-", ""))}">${esc(c.company_name)} · ${esc(c.customer_id)}</option>`
    ).join("");
    if ([...select.options].some(o => o.value === current)) select.value = current;
  } catch (error) { /* keep static fallback options */ }
}

async function loadLoginCustomerUsers() {
  const select = $("loginCustomerUser");
  if (!select) return;
  try {
    const response = await fetch("/api/v2/auth/customer-users");
    const users = await response.json();
    select.innerHTML = users.map(u =>
      `<option value="${esc(u.employee_id)}" data-customer-id="${esc(u.customer_id || "")}">${esc(u.company_name)} · ${esc(u.employee_id)}</option>`
    ).join("");
  } catch (error) {
    select.innerHTML = '<option value="USER-MP-001" data-customer-id="COMP-MP">Công ty TNHH Minh Phát · USER-MP-001</option>';
  }
}

function showCustomerRegistration(show) {
  $("loginForm").classList.toggle("hidden", show);
  $("customerRegistrationForm").classList.toggle("hidden", !show);
  $("registrationError").textContent = "";
  if (show) $("registerCompanyName").focus();
}

async function registerCustomerUser(event) {
  event.preventDefault();
  $("registrationError").textContent = "";
  try {
    const response = await fetch("/api/v2/auth/customer-users", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        company_name: $("registerCompanyName").value,
        tax_code: $("registerTaxCode").value,
        industry: $("registerIndustry").value,
        contact_name: $("registerContact").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message || "Không thể tạo hồ sơ.");
    await Promise.all([loadLoginCustomerUsers(), loadSessionCompanies()]);
    $("loginRole").value = "customer";
    $("loginCustomerUser").value = data.employee_id;
    sessionStorage.setItem("shb_customer_id", data.customer_id);
    sessionStorage.setItem("shb_company_name", data.company_name);
    ensureCustomerSessionOption(data.customer_id, data.company_name);
    showCustomerRegistration(false);
    syncLoginCustomerVisibility();
    $("loginRoleHint").textContent = `Đã tạo ${data.employee_id}. Nhập mật khẩu demo để đăng nhập.`;
    $("loginPassword").focus();
  } catch (error) {
    $("registrationError").textContent = error.message;
  }
}

function logout() {
  authToken = "";
  sessionStorage.removeItem("shb_access_token");
  $("employee").value = "RM-999";
  $("session").disabled = false;
  $("roleBadge").textContent = "Chưa đăng nhập";
  $("loginScreen").style.display = "flex";
  hideAllWorkspaces();
}

function renderCustomerPendingFiles(){
  $("customerPendingFiles").innerHTML=customerUi.pendingFiles.map(file=>`<div class="file-item"><span class="file-icon">${esc(file.name.split(".").pop().toUpperCase())}</span><div><strong>${esc(file.name)}</strong><small>${Math.ceil(file.size/1024)} KB · chờ tải lên</small></div></div>`).join("");
}

function showCustomerCase(data,message){
  customerUi.caseId=data.case_id;customerUi.version=data.version;
  $("customerDocuments").classList.remove("hidden");
  $("customerStatusTitle").textContent=message||"Đã gửi RM tiếp nhận";
  $("customerStatusHelp").textContent="RM sẽ đối chiếu hồ sơ, xác nhận context và chịu trách nhiệm cho mọi bước phân tích/phê duyệt tiếp theo.";
  $("customerCurrentCase").classList.remove("hidden");
  $("customerCurrentCase").innerHTML=`<b>${esc(data.case_id)}</b><br><small>Trạng thái: ${esc(statusLabels[data.intake_status]||data.intake_status)}</small>`;
}

async function submitCustomerIntake(){
  try{
    const data=await api("/api/v2/sales-cases",{method:"POST",headers:{"Idempotency-Key":`customer-ui-${Date.now()}`},body:JSON.stringify({
      company_name:$("customerCompanyName").value,tax_code:$("customerTaxCode").value,industry:$("customerIndustry").value,
      contact:$("customerContact").value,employees_count:Number($("customerEmployees").value)||null,
      annual_revenue:Number($("customerRevenue").value)||null,operating_years:Number($("customerOperatingYears").value)||null,
      requested_amount_vnd:Number($("customerRequestedAmount").value)||null,preferred_timeline:$("customerTimeline").value,
      need_text:$("customerNeedText").value,rm_note:"Thông tin do Customer User cung cấp; RM cần đối chiếu trước khi xác nhận.",priority:"normal",current_products:[]
    })});
    showCustomerCase(data,"Đã gửi thông tin cơ bản");
    customerUi.pendingFiles=[newMockFile("registration")];renderCustomerPendingFiles();await loadCustomerCases();
    toast(`Đã tạo ${esc(data.case_id)}. Có thể đính kèm hồ sơ trước khi RM xử lý.`);
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}

async function uploadCustomerDocuments(){
  if(!customerUi.caseId)return toast("Hãy gửi phiếu thông tin trước.","warning");
  if(!customerUi.pendingFiles.length)return toast("Chưa có hồ sơ đính kèm.","warning");
  try{
    const form=new FormData();customerUi.pendingFiles.forEach(file=>form.append("files",file));
    let data=await api(`/api/v2/sales-cases/${customerUi.caseId}/documents`,{method:"POST",body:form});
    customerUi.version=data.version;
    data=await api(`/api/v2/sales-cases/${customerUi.caseId}/process-documents`,{method:"POST"});
    customerUi.version=data.version;customerUi.pendingFiles=[];renderCustomerPendingFiles();
    showCustomerCase(data,"Đã gửi hồ sơ — chờ RM xác nhận");await loadCustomerCases();
    toast("Hồ sơ đã được kiểm tra, trích xuất và chuyển tới RM. Customer User không thể tự xác nhận context.");
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}

async function loadCustomerCases(){
  try{
    const items=await api("/api/v2/sales-cases");
    $("customerCaseList").innerHTML=items.length?items.slice(0,8).map(item=>`<div class="customer-case-item"><b>${esc(item.case_id)}</b><br><span>${esc(statusLabels[item.runtime_status||item.intake_status]||item.runtime_status||item.intake_status)}</span><br><small>${esc(item.manual_input?.need_text||"")}</small></div>`).join(""):'<p class="muted">Chưa có hồ sơ.</p>';
  }catch(error){toast(`Không tải được hồ sơ đã gửi: ${esc(error.message)}`,"error")}
}

function creditRequestPayload(){
  return {
    customer_id:loginCustomerId(),
    company_name:$("creditCompanyName").value,
    tax_id:$("creditTaxId").value,
    legal_type:$("creditLegalType").value,
    representative:$("creditRepresentative").value,
    industry:$("creditIndustry").value,
    business_scale:$("creditScale").value,
    total_assets_billion_vnd:Number($("creditAssets").value),
    net_revenue_billion_vnd:Number($("creditRevenue").value),
    net_profit_billion_vnd:Number($("creditProfit").value),
    debt_to_equity_ratio:Number($("creditDebtEquity").value),
    cic_debt_classification:$("creditCic").value,
    current_debt_billion_vnd:Number($("creditCurrentDebt").value),
    collateral_description:$("creditCollateral").value,
    collateral_value_billion_vnd:Number($("creditCollateralValue").value),
    casa_avg_balance_billion_vnd:Number($("creditCasa").value),
    repayment_history:$("creditRepayment").value,
    request_type:document.querySelector('input[name="creditRequestType"]:checked').value,
    requested_amount_vnd:Number($("creditAmount").value),
    requested_term_months:Number($("creditTerm").value)||null,
    purpose:$("creditPurpose").value
  };
}

// Idempotency: key = SHA-256 của nội dung form. Cùng nội dung -> cùng key,
// server (unique index submitted_by + submission_idempotency_key) trả lại
// bản ghi cũ thay vì tạo bản trùng khi bấm gửi nhiều lần.
async function creditIdempotencyKey(payload){
  const bytes=new TextEncoder().encode(JSON.stringify(payload));
  const hash=await crypto.subtle.digest("SHA-256",bytes);
  return "credit-"+Array.from(new Uint8Array(hash)).map(b=>b.toString(16).padStart(2,"0")).join("").slice(0,48);
}

function formatServiceRecommendation(row){
  const services=Array.isArray(row.service_recommendation)?row.service_recommendation:[];
  if(!services.length)return "";
  return `<ul>${services.map(s=>`<li><b>${esc(s.service)}</b> (${esc(s.priority)}) — ${esc(s.reason)}</li>`).join("")}</ul>`;
}

function creditAgentBlocksHtml(row,{showInternal=true}={}){
  if(!showInternal){
    return `<div class="notice"><b>Trạng thái hồ sơ:</b> ${esc(creditStatusVi(row.status))}</div>`;
  }
  const rawSummary=row.service_recommendation_summary||"";
  const isLlm=rawSummary.startsWith("[AI");
  const summary=rawSummary.replace(/^\[(AI:Gemini|Rule)\]\s*/,"");
  const hasServices=Array.isArray(row.service_recommendation)&&row.service_recommendation.length;
  const srcBadge=hasServices?`<span class="src-badge ${isLlm?"src-llm":"src-rule"}">${isLlm?"AI thật (Gemini)":"Rule"}</span>`:"";
  const services=summary||hasServices?`
    <fieldset class="credit-section">
      <legend>7. Agent · Gợi ý dịch vụ cho RM ${srcBadge}</legend>
      <div class="notice success">
        <b>${esc(summary||"Đề xuất dịch vụ")}</b>
        ${formatServiceRecommendation(row)}
        ${row.rm_note?`<p><small>Ghi chú RM: ${esc(row.rm_note)}</small></p>`:""}
      </div>
    </fieldset>`:"";
  const specialist=row.specialist_recommendation?`
    <fieldset class="credit-section">
      <legend>8. Chuyên viên · Kết quả thẩm định</legend>
      <p><b>${esc(row.specialist_recommendation)}</b> — ${esc(row.specialist_reason||"")}</p>
    </fieldset>`:"";
  const disbursement=row.appraisal_summary?`
    <fieldset class="credit-section">
      <legend>9. Agent · Khuyến nghị giải ngân</legend>
      <div class="notice ${row.agent_recommendation==="recommend"?"success":"warning"}">
        <b>${row.agent_recommendation==="recommend"?"Nên xem xét giải ngân":"Không khuyến nghị giải ngân"} (${esc(row.appraisal_score)}/100)</b><br>${esc(row.appraisal_summary)}
        <p><small>Chỉ là khuyến nghị; Manager chịu trách nhiệm quyết định cuối.</small></p>
      </div>
    </fieldset>`:"";
  const decision=row.final_decision||row.decision_reason?`
    <fieldset class="credit-section">
      <legend>10. Quyết định cuối của Manager</legend>
      <p><b>${esc(row.final_decision||row.status)}</b> — ${esc(row.decision_reason||"")}</p>
    </fieldset>`:"";
  return services+specialist+disbursement+decision;
}

function creditReadonlyFieldsHtml(row){
  const typeLabel={loan:"Khoản vay",service:"Dịch vụ",both:"Cả hai"}[row.request_type]||row.request_type;
  return `
    <fieldset class="credit-section"><legend>1. Thông tin KYC</legend>
      <div class="form-grid">
        <label class="field">Tên công ty<input value="${esc(row.company_name)}" readonly></label>
        <label class="field">Mã số thuế<input value="${esc(row.tax_id)}" readonly></label>
        <label class="field">Loại hình pháp lý<input value="${esc(row.legal_type)}" readonly></label>
        <label class="field">Người đại diện<input value="${esc(row.representative)}" readonly></label>
      </div>
    </fieldset>
    <fieldset class="credit-section"><legend>2. Hoạt động kinh doanh</legend>
      <div class="form-grid">
        <label class="field">Ngành nghề chính<input value="${esc(row.industry)}" readonly></label>
        <label class="field">Quy mô<input value="${esc(row.business_scale)}" readonly></label>
      </div>
    </fieldset>
    <fieldset class="credit-section"><legend>3. Chỉ số tài chính (tỷ VND)</legend>
      <div class="form-grid">
        <label class="field">Tổng tài sản<input value="${esc(row.total_assets_billion_vnd)}" readonly></label>
        <label class="field">Doanh thu thuần<input value="${esc(row.net_revenue_billion_vnd)}" readonly></label>
        <label class="field">Lợi nhuận sau thuế<input value="${esc(row.net_profit_billion_vnd)}" readonly></label>
        <label class="field">Tỷ số D/E<input value="${esc(row.debt_to_equity_ratio)}" readonly></label>
      </div>
    </fieldset>
    <fieldset class="credit-section"><legend>4. CIC và rủi ro</legend>
      <div class="form-grid">
        <label class="field">Phân loại nợ (CIC)<input value="${esc(row.cic_debt_classification)}" readonly></label>
        <label class="field">Dư nợ hiện tại (tỷ VND)<input value="${esc(row.current_debt_billion_vnd)}" readonly></label>
        <label class="field span-2">Tài sản đảm bảo<input value="${esc(row.collateral_description)}" readonly></label>
        <label class="field">Giá trị TSĐB (tỷ VND)<input value="${esc(row.collateral_value_billion_vnd)}" readonly></label>
      </div>
    </fieldset>
    <fieldset class="credit-section"><legend>5. Lịch sử giao dịch</legend>
      <div class="form-grid">
        <label class="field">CASA bình quân (tỷ VND)<input value="${esc(row.casa_avg_balance_billion_vnd)}" readonly></label>
        <label class="field">Lịch sử trả nợ<input value="${esc(row.repayment_history)}" readonly></label>
      </div>
    </fieldset>
    <fieldset class="credit-section"><legend>6. Đề nghị vay</legend>
      <p class="muted">${esc(typeLabel)} · ${Number(row.requested_amount_vnd).toLocaleString("vi-VN")} VND · ${esc(row.requested_term_months||"—")} tháng</p>
      <label class="field span-2">Mục đích<textarea rows="3" readonly>${esc(row.purpose)}</textarea></label>
    </fieldset>`;
}

function creditStaffActionsHtml(row,role){
  if(role==="relationship_manager" && row.status==="WithRM"){
    return `<div class="credit-approval-actions">
      <textarea id="creditSharedRmNote" placeholder="Ghi chú khi chuyển sang bước thẩm định (tuỳ chọn)" aria-label="Ghi chú"></textarea>
      <button class="button primary" type="button" onclick="forwardCreditRequest('${row.request_id}',this)">Hoàn tất hồ sơ & chuyển sang thẩm định →</button>
    </div>`;
  }
  // Merged bank-staff persona: the same person forwards then appraises.
  if((role==="credit_specialist"||role==="relationship_manager") && row.status==="PendingAppraisal"){
    return `<div class="credit-approval-actions">
      <textarea id="creditSharedAppraisalReason" placeholder="Nhận xét thẩm định của chuyên viên..." aria-label="Nhận xét thẩm định"></textarea>
      <button class="button primary" type="button" onclick="appraiseCreditRequest('${row.request_id}','recommend')">Đề nghị trình phê duyệt</button>
      <button class="button secondary" type="button" onclick="appraiseCreditRequest('${row.request_id}','needs_more_information')">Yêu cầu RM bổ sung</button>
      <button class="button danger" type="button" onclick="appraiseCreditRequest('${row.request_id}','not_recommended')">Không đề nghị</button>
    </div>`;
  }
  if(role==="manager" && row.status==="PendingFinalApproval"){
    return `<div class="credit-approval-actions">
      <textarea id="creditSharedReason" placeholder="Lý do quyết định cuối của Manager..." aria-label="Lý do quyết định"></textarea>
      <button class="button primary" type="button" onclick="decideCreditRequest('${row.request_id}','approved')">Phê duyệt giải ngân</button>
      <button class="button secondary" type="button" onclick="decideCreditRequest('${row.request_id}','needs_more_information')">Trả lại thẩm định</button>
      <button class="button danger" type="button" onclick="decideCreditRequest('${row.request_id}','rejected')">Từ chối</button>
    </div>`;
  }
  return `<p class="muted">Không có thao tác cho trạng thái ${esc(row.status)}.</p>`;
}

function showCustomerAgentOnForm(row){
  const box=$("creditAgentOnForm");
  if(!box)return;
  box.classList.remove("hidden");
  box.innerHTML=creditAgentBlocksHtml(row,{showInternal:false})+
    `<p class="muted">Bạn chỉ xem form và trạng thái công khai. Gợi ý Agent, nhận xét thẩm định và nội dung phê duyệt là dữ liệu nội bộ.</p>`;
}

let _creditRowsCache=[];
const realCreditRows = rows => rows.filter(row => !String(row.request_id || "").startsWith("CR-MOCK-"));

async function submitCreditRequest(event){
  event.preventDefault();
  const button=event.target.querySelector('button[type="submit"]');
  button.disabled=true;
  try{
    const payload=creditRequestPayload();
    const row=await api("/api/v2/credit-requests",{
      method:"POST",
      headers:{"Idempotency-Key":await creditIdempotencyKey(payload)},
      body:JSON.stringify(payload)
    });
    const result=$("creditSubmissionResult");
    result.className="credit-result";
    result.innerHTML=`<b>Đã gửi ${esc(row.request_id)}</b><small> · ${esc(row.status)}</small>`;
    showCustomerAgentOnForm(row);
    await loadCustomerCreditRequests();
    toast(`Đã gửi form ${esc(row.request_id)} cho RM xử lý.`);
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
  finally{button.disabled=false}
}

async function loadCustomerCreditRequests(){
  try{
    const rows=realCreditRows(await api("/api/v2/credit-requests"));
    _creditRowsCache=rows;
    $("creditRequestList").innerHTML=rows.length?rows.map(row=>`
      <button type="button" class="customer-case-item credit-list-item" onclick="openCustomerCreditForm('${row.request_id}')">
        <b>${esc(row.request_id)}</b><br>
        <span>${esc(creditStatusVi(row.status))}</span><br>
        <small>${esc(row.status==="WithRM"?"Đang chờ RM":row.status==="PendingAppraisal"?"Đang thẩm định":row.status==="PendingFinalApproval"?"Đang chờ phê duyệt cuối":"Đã xử lý")}</small>
      </button>`).join(""):'<p class="muted">Chưa có yêu cầu.</p>';
  }catch(error){$("creditRequestList").innerHTML=`<p class="muted">${esc(error.message)}</p>`}
}

function openCustomerCreditForm(requestId){
  const row=_creditRowsCache.find(r=>r.request_id===requestId);
  if(!row)return;
  showCustomerAgentOnForm(row);
  $("creditCompanyName").value=row.company_name;
  $("creditTaxId").value=row.tax_id;
  $("creditLegalType").value=row.legal_type;
  $("creditRepresentative").value=row.representative;
  $("creditIndustry").value=row.industry;
  $("creditScale").value=row.business_scale;
  $("creditAssets").value=row.total_assets_billion_vnd;
  $("creditRevenue").value=row.net_revenue_billion_vnd;
  $("creditProfit").value=row.net_profit_billion_vnd;
  $("creditDebtEquity").value=row.debt_to_equity_ratio;
  $("creditCic").value=row.cic_debt_classification;
  $("creditCurrentDebt").value=row.current_debt_billion_vnd;
  $("creditCollateral").value=row.collateral_description;
  $("creditCollateralValue").value=row.collateral_value_billion_vnd;
  $("creditCasa").value=row.casa_avg_balance_billion_vnd;
  $("creditRepayment").value=row.repayment_history;
  $("creditAmount").value=row.requested_amount_vnd;
  $("creditTerm").value=row.requested_term_months||"";
  $("creditPurpose").value=row.purpose;
  const typeRadio=document.querySelector(`input[name="creditRequestType"][value="${row.request_type}"]`);
  if(typeRadio)typeRadio.checked=true;
  const locked=row.status!=="draft";
  $("creditRequestForm").querySelectorAll("input,select,textarea,button[type=submit]").forEach(el=>{
    if(el.type==="radio")el.disabled=locked;
    else if(el.tagName==="BUTTON")el.disabled=locked;
    else el.readOnly=locked;
  });
  toast(`Đã mở tờ trình ${esc(requestId)} trên form.`);
}

// Customer form -> RM -> specialist appraisal -> Manager final approval.
function renderHero(rows){
  const flow=$("heroFlow");
  if(!flow)return;
  const count=status=>rows.filter(r=>r.status===status).length;
  const mainSteps=[["WithRM","① Chờ RM"],["PendingAppraisal","② Chờ thẩm định"],["PendingFinalApproval","③ Chờ Manager"],["Approved","④ Đã duyệt giải ngân"]];
  const mainHtml=mainSteps.map(([status,label],index)=>
    `<span class="${count(status)?"flow-active":""}">${label}: ${count(status)}</span>${index<mainSteps.length-1?"<i>→</i>":""}`).join("");
  flow.innerHTML=`${mainHtml}<i>↘</i><span class="flow-reject">✕ Từ chối (RM/cuối): ${count("Rejected")}</span>`;
}

function creditStatusVi(status){
  return {WithRM:"Chờ RM",PendingAppraisal:"Chờ chuyên viên thẩm định",PendingFinalApproval:"Chờ Manager phê duyệt",Approved:"Đã duyệt · giải ngân",Rejected:"Từ chối"}[status]||status;
}

function creditRecordFlowHtml(row){
  const steps=[["WithRM","① Form khách hàng"],["PendingAppraisal","② Chuyên viên thẩm định"],["PendingFinalApproval","③ Agent khuyến nghị"],["Approved","④ Manager duyệt"]];
  const rank={WithRM:0,PendingAppraisal:1,PendingFinalApproval:2,Approved:3,Rejected:-1};
  const current=rank[row.status]??0;
  const rejected=row.status==="Rejected";
  const main=steps.map(([_,label],index)=>{
    let cls="";
    if(rejected)cls=index===0?"done":"";
    else if(index<current)cls="done";
    else if(index===current)cls="active";
    return `<span class="${cls}">${label}</span>${index<steps.length-1?"<i>→</i>":""}`;
  }).join("");
  return `<div class="record-flow" aria-label="Luồng hồ sơ hiện tại">${main}${rejected?'<i>↘</i><span class="active reject">✕ Từ chối</span>':""}</div>`;
}

function creditPickerHtml(rows,selectedId,onChangeName){
  if(!rows.length)return '<p class="muted">Không có tờ trình.</p>';
  return `<label>Chọn tờ trình
    <select onchange="${onChangeName}(this.value)">
      ${rows.map(row=>`<option value="${esc(row.request_id)}" ${row.request_id===selectedId?"selected":""}>${esc(row.request_id)} · ${creditStatusVi(row.status)}</option>`).join("")}
    </select>
  </label>`;
}

function renderCreditFormView(container,row,role){
  if(!container)return;
  container.innerHTML=`
    <p><b>${esc(row.request_id)}</b> · ${creditStatusVi(row.status)}</p>
    ${creditRecordFlowHtml(row)}
    ${creditReadonlyFieldsHtml(row)}
    ${creditAgentBlocksHtml(row,{showInternal:true})}
    ${creditStaffActionsHtml(row,role)}`;
}

async function loadRmCreditForwardQueue(){
  const picker=$("rmCreditPicker");
  const view=$("rmCreditFormView");
  if(!picker||!view)return;
  try{
    const rows=realCreditRows(await api("/api/v2/credit-requests"));
    _creditRowsCache=rows;
    renderHero(rows);
    const waiting=rows.filter(row=>row.status==="WithRM"||row.status==="PendingAppraisal");
    const focus=waiting[0]||rows[0];
    picker.innerHTML=creditPickerHtml(rows,focus?.request_id,"openRmCreditForm");
    if(focus)renderCreditFormView(view,focus,"relationship_manager");
    else view.innerHTML='<p class="muted">Không có tờ trình trong phạm vi.</p>';
  }catch(error){picker.innerHTML="";view.innerHTML=`<p class="muted">${esc(error.message)}</p>`}
}

function openRmCreditForm(requestId){
  const row=_creditRowsCache.find(r=>r.request_id===requestId);
  if(!row)return;
  renderCreditFormView($("rmCreditFormView"),row,"relationship_manager");
}

async function forwardCreditRequest(requestId,btn){
  const note=($("creditSharedRmNote")?.value||"").trim();
  if(btn)btn.disabled=true;
  try{
    const row=await api(`/api/v2/credit-requests/${requestId}/forward`,{
      method:"POST",
      headers:{"Idempotency-Key":`credit-forward-${requestId}-${Date.now()}`},
      body:JSON.stringify({rm_note:note})
    });
    toast(`Đã chuyển trên form · Agent #2: ${esc(row.service_recommendation_summary||"đã đề xuất")}`);
    await loadRmCreditForwardQueue();
  }catch(error){
    if(error.code==="CREDIT_REQUEST_CONFLICT"){
      toast("Tờ trình này đã được chuyển hoặc quyết định rồi — đang tải lại trạng thái mới.","warning");
      await loadRmCreditForwardQueue();
    }else toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error");
  }finally{if(btn)btn.disabled=false}
}

async function loadCreditApprovalRequests(){
  const panel=$("creditApprovalPanel");
  const picker=$("csCreditPicker");
  const view=$("csCreditFormView");
  if(!panel||!picker||!view)return;
  try{
    const rows=realCreditRows(await api("/api/v2/credit-requests"));
    _creditRowsCache=rows;
    panel.classList.remove("hidden");
    const queue=rows.filter(row=>row.status==="PendingAppraisal"||row.specialist_recommendation);
    const focus=queue.find(r=>r.status==="PendingAppraisal")||queue[0]||rows[0];
    picker.innerHTML=creditPickerHtml(queue.length?queue:rows,focus?.request_id,"openCsCreditForm");
    if(focus)renderCreditFormView(view,focus,"credit_specialist");
    else view.innerHTML='<p class="muted">Không có tờ trình.</p>';
  }catch(error){panel.classList.remove("hidden");picker.innerHTML="";view.innerHTML=`<p class="muted">${esc(error.message)}</p>`}
}

function openCsCreditForm(requestId){
  const row=_creditRowsCache.find(r=>r.request_id===requestId);
  if(!row)return;
  const panel=$("creditApprovalPanel");
  if(!panel||panel.classList.contains("hidden")){
    toast("Form phê duyệt tờ trình chỉ mở cho Credit Specialist.","warning");
    return;
  }
  renderCreditFormView($("csCreditFormView"),row,"credit_specialist");
  panel.scrollIntoView({behavior:"smooth",block:"start"});
}

async function decideCreditRequest(requestId,decision){
  const reason=($("creditSharedReason")?.value||"").trim();
  if(reason.length<5)return toast("Hãy nhập lý do quyết định (ít nhất 5 ký tự).","warning");
  try{
    await api(`/api/v2/credit-requests/${requestId}/decision`,{
      method:"POST",
      headers:{"Idempotency-Key":`credit-decision-${requestId}-${Date.now()}`},
      body:JSON.stringify({decision,reason})
    });
    await loadManagerApprovalRequests();
    toast(`Đã lưu quyết định ${esc(decision)} trên form ${esc(requestId)}.`);
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}

async function appraiseCreditRequest(requestId,recommendation){
  const reason=($("creditSharedAppraisalReason")?.value||"").trim();
  if(reason.length<5)return toast("Hãy nhập nhận xét thẩm định (ít nhất 5 ký tự).","warning");
  try{
    await api(`/api/v2/credit-requests/${requestId}/appraisal`,{
      method:"POST",
      headers:{"Idempotency-Key":`credit-appraisal-${requestId}-${Date.now()}`},
      body:JSON.stringify({recommendation,reason})
    });
    // Reload whichever workspace the merged staff persona is looking at.
    if(!$("rmWorkspace").classList.contains("hidden"))await loadRmCreditForwardQueue();
    else await loadCreditApprovalRequests();
    toast("Đã lưu thẩm định; Agent đã tạo khuyến nghị giải ngân để người phê duyệt cuối xem xét.");
  }catch(error){toast(`<b>${esc(error.code)}:</b> ${esc(error.message)}`,"error")}
}

async function loadManagerApprovalRequests(){
  const picker=$("managerCreditPicker"),view=$("managerCreditFormView");
  if(!picker||!view)return;
  try{
    const rows=realCreditRows(await api("/api/v2/credit-requests"));
    _creditRowsCache=rows;
    const queue=rows.filter(row=>row.status==="PendingFinalApproval"||row.final_decision);
    const focus=queue.find(row=>row.status==="PendingFinalApproval")||queue[0];
    picker.innerHTML=creditPickerHtml(queue,focus?.request_id,"openManagerCreditForm");
    if(focus)renderCreditFormView(view,focus,"manager");
    else view.innerHTML='<p class="muted">Không có tờ trình chờ phê duyệt cuối.</p>';
  }catch(error){picker.innerHTML="";view.innerHTML=`<p class="muted">${esc(error.message)}</p>`}
}

function openManagerCreditForm(requestId){
  const row=_creditRowsCache.find(item=>item.request_id===requestId);
  if(row)renderCreditFormView($("managerCreditFormView"),row,"manager");
}

async function loadNextBestWorkQueue() {
  try {
    const data = await api("/api/v2/me/work-queue");
    const queue = Array.isArray(data) ? data : (data?.queue || []);
    const container = $("nbwQueueList");
    if (!queue.length) {
      container.innerHTML = '<p class="muted">Không có nhiệm vụ ưu tiên nào.</p>';
      return;
    }

    container.innerHTML = queue.slice(0,5).map(item => {
      const priorityClass = item.priority_score >= 80 ? "high" : (item.priority_score >= 50 ? "medium" : "low");
      const bandLabel = item.priority_band === 0 ? "P0 Regulatory" : (item.priority_band === 1 ? "P1 SLA" : (item.priority_band === 2 ? "P2 Customer" : "P3 Normal"));
      const suggestions = (item.agent_suggestions && item.agent_suggestions.length)
        ? item.agent_suggestions.join(" · ")
        : item.recommended_action;
      return `
        <div class="nbw-item ${priorityClass}" onclick="toast('Nhiệm vụ: ${esc(item.title)}. Lý do: ${esc(item.reasons.join('; '))}', 'warning')">
          <span class="nbw-badge ${priorityClass}">${bandLabel} · ${item.priority_score} pts</span>
          <h4>${esc(item.title)}</h4>
          <p>Khách hàng: <b>${esc(item.customer_id || "—")}</b></p>
          <p><b>Gợi ý Agent:</b> ${esc(suggestions)}</p>
          <small class="muted" style="display:block; margin-top:4px;">Lý do: ${esc(item.reasons.join(", "))}</small>
        </div>
      `;
    }).join("");
  } catch (error) {
    toast(`Lỗi khi tải NBW: ${esc(error.message)}`, "error");
  }
}

async function loadSpecialistQueue() {
  try {
    const data = await api("/api/v2/me/work-queue");
    const queue = Array.isArray(data) ? data : (data?.queue || []);
    const container = $("specQueueList");
    if (!queue.length) {
      container.innerHTML = '<p class="muted">Không có hồ sơ chờ xử lý.</p>';
      return;
    }

    container.innerHTML = queue.map(item => `
      <div class="nbw-item medium" onclick="viewSpecialistTask('${item.work_item_id}')">
        <h4>${esc(item.title)}</h4>
        <p>Khách hàng: <b>${esc(item.customer_id)}</b> · Trạng thái: <code>${esc(item.status)}</code></p>
      </div>
    `).join("");
  } catch (error) {
    toast(`Lỗi tải Specialist queue: ${esc(error.message)}`, "error");
  }
}

// Agent Knowledge Console: lets a department Specialist feed/update/retire
// the knowledge their own domain's Agent (Product/Credit/Insurance)
// retrieves, and see a metadata summary of what that Agent has been doing
// on cases in their scope. Backed by app/api/v2/knowledge_router.py
// (/api/v2/me/agent-knowledge). Domain is decided server-side from the
// specialist's role -- never sent from this UI.
const akDomainLabel = {product: "Product Agent", legal: "Legal/Compliance Rules", credit: "Credit Agent", insurance: "Insurance Agent"};

async function loadAgentKnowledgeConsole() {
  const dateField = $("akEffectiveFrom");
  if (dateField && !dateField.value) dateField.value = new Date().toISOString().slice(0, 10);
  try {
    const list = await api("/api/v2/me/agent-knowledge");
    if (list.length) $("akTitle").textContent = `Tri thức của ${akDomainLabel[list[0].domain] || "Agent phòng ban"}`;
    renderAgentKnowledgeEntries(list);
  } catch (error) {
    $("akEntryList").innerHTML = `<p class="muted">Lỗi tải tri thức: ${esc(error.message)}</p>`;
  }
}

function renderAgentKnowledgeEntries(list) {
  const container = $("akEntryList");
  if (!list.length) { container.innerHTML = '<p class="muted">Chưa có tri thức nào được nạp cho Agent này.</p>'; return; }
  container.innerHTML = list.map(item => {
    const statusChips = [
      item.is_superseded ? '<span class="ak-chip superseded">SUPERSEDED</span>' : '<span class="ak-chip active">ACTIVE</span>',
      item.is_quarantined ? '<span class="ak-chip quarantined">QUARANTINED</span>' : "",
    ].join("");
    return `
      <div class="ak-entry ${item.is_superseded ? "superseded" : ""} ${item.is_quarantined ? "quarantined" : ""}">
        <h4>${esc(item.product_id)} · ${esc(item.section_path)}</h4>
        <p>${statusChips}</p>
        <p>${esc(item.text)}</p>
        <p class="muted">Nạp bởi ${esc(item.contributed_by)} · ${esc(item.contributed_at ? new Date(item.contributed_at).toLocaleString("vi-VN") : "—")}</p>
        ${!item.is_superseded ? `
        <div class="ak-entry-actions">
          <button class="button ghost" type="button" onclick="editAgentKnowledgeEntry('${item.chunk_id}')">Sửa nội dung</button>
          <button class="button ghost" type="button" onclick="toggleAgentKnowledgeQuarantine('${item.chunk_id}', ${!item.is_quarantined})">${item.is_quarantined ? "Bật lại" : "Ẩn khỏi Agent"}</button>
        </div>` : ""}
      </div>
    `;
  }).join("");
}

async function submitAgentKnowledgeEntry(event) {
  event.preventDefault();
  const body = {
    product_id: $("akProductId").value.trim(),
    section_path: $("akSectionPath").value.trim(),
    text: $("akText").value.trim(),
    effective_from: $("akEffectiveFrom").value,
  };
  try {
    await api("/api/v2/me/agent-knowledge", {method: "POST", body: JSON.stringify(body)});
    $("akText").value = "";
    toast("Đã nạp tri thức mới cho Agent.", "success");
    loadAgentKnowledgeConsole();
    loadCreditHistory();
  } catch (error) {
    toast(`<b>${esc(error.code || "API_ERROR")}:</b> ${esc(error.message)}`, "error");
  }
  return false;
}

async function editAgentKnowledgeEntry(chunkId) {
  const text = prompt("Nội dung tri thức mới (sẽ tạo phiên bản mới, giữ lại bản cũ):");
  if (!text || !text.trim()) return;
  try {
    await api(`/api/v2/me/agent-knowledge/${encodeURIComponent(chunkId)}`, {method: "PATCH", body: JSON.stringify({text: text.trim()})});
    toast("Đã cập nhật tri thức (phiên bản mới).", "success");
    loadAgentKnowledgeConsole();
  } catch (error) {
    toast(`<b>${esc(error.code || "API_ERROR")}:</b> ${esc(error.message)}`, "error");
  }
}

async function toggleAgentKnowledgeQuarantine(chunkId, next) {
  try {
    await api(`/api/v2/me/agent-knowledge/${encodeURIComponent(chunkId)}`, {method: "PATCH", body: JSON.stringify({is_quarantined: next})});
    toast(next ? "Đã ẩn tri thức khỏi Agent." : "Đã bật lại tri thức cho Agent.", "success");
    loadAgentKnowledgeConsole();
  } catch (error) {
    toast(`<b>${esc(error.code || "API_ERROR")}:</b> ${esc(error.message)}`, "error");
  }
}

// Lịch sử tờ trình: business-facing timeline per credit request
// (khách gửi -> Agent thẩm định -> RM chuyển -> quyết định cuối).
// Thay thế panel Agent Activity kỹ thuật cũ; dữ liệu lấy từ các cột
// timestamp/decision đã có trong corporate_credit_requests, không cần API mới.
let _creditHistoryFilter = "open";

function setCreditHistoryFilter(filter) {
  _creditHistoryFilter = filter;
  document.querySelectorAll(".credit-history-filters .button").forEach(button => {
    button.classList.toggle("is-selected", button.dataset.filter === filter);
  });
  loadCreditHistory();
}

function creditHistoryTimeToText(value) {
  return value ? new Date(value).toLocaleString("vi-VN", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : "";
}

function creditHistoryStepsHtml(row) {
  const decidedLabel = {approved: "Phê duyệt", rejected: "Từ chối", needs_more_information: "Trả RM bổ sung"}[row.final_decision] || row.final_decision;
  const steps = [
    {done: true, text: `Khách gửi tờ trình · ${creditHistoryTimeToText(row.submitted_at)}`},
    {done: !!row.appraised_at, text: row.appraised_at
      ? `Agent #1: ${esc(row.agent_recommendation || "—")} (score ${row.appraisal_score ?? "—"}) · ${creditHistoryTimeToText(row.appraised_at)}`
      : "Agent thẩm định — chưa chạy"},
    {done: row.status !== "WithRM", text: row.status !== "WithRM"
      ? `RM đã chuyển phê duyệt${row.rm_note ? ` · “${esc(row.rm_note)}”` : ""}`
      : "Đang chờ RM chuyển"},
    {done: !!row.final_decision, text: row.final_decision
      ? `${esc(decidedLabel)} bởi ${esc(row.approved_by || "chuyên gia")} · ${creditHistoryTimeToText(row.decided_at)}${row.decision_reason ? `<br>Lý do: “${esc(row.decision_reason)}”` : ""}`
      : "Chờ quyết định cuối"},
  ];
  return `<ol class="credit-history-steps">${steps.map(step => `<li class="${step.done ? "" : "step-pending"}">${step.text}</li>`).join("")}</ol>`;
}

async function loadCreditHistory() {
  const container = $("creditHistoryList");
  if (!container) return;
  try {
    const rows = realCreditRows(await api("/api/v2/credit-requests"));
    _creditRowsCache = rows;
    const isOpen = row => row.status === "WithRM" || row.status === "PendingApproval";
    const filtered = _creditHistoryFilter === "open" ? rows.filter(isOpen)
      : _creditHistoryFilter === "decided" ? rows.filter(row => !isOpen(row))
      : rows;
    if (!filtered.length) { container.innerHTML = '<p class="muted">Không có tờ trình trong mục này.</p>'; return; }
    container.innerHTML = filtered.map(row => `
      <button type="button" class="credit-history-item" onclick="openCsCreditForm('${row.request_id}')">
        <b>${esc(row.request_id)}</b> · ${esc(row.company_name)} · ${Number(row.requested_amount_vnd).toLocaleString("vi-VN")} VND
        <span class="plain-status" style="float:right;">${esc(row.status)}</span>
        ${creditHistoryStepsHtml(row)}
      </button>
    `).join("");
  } catch (error) {
    container.innerHTML = `<p class="muted">Lỗi tải lịch sử tờ trình: ${esc(error.message)}</p>`;
  }
}

async function viewSpecialistTask(taskId) {
  try {
    const data = await api("/api/v2/me/work-queue");
    const queue = Array.isArray(data) ? data : (data?.queue || []);
    const item = queue.find(x => x.work_item_id === taskId);
    if (!item) return;

    const allowedActions = item.allowed_actions || [item.recommended_action];
    const excludedActions = item.excluded_actions || [];

    // Parse case_id and case_version from item_id
    const match = taskId.match(/REVIEW-NOTIFY-(CASE-\d+)-(\d+)-/);
    let caseId = "";
    let caseVersion = 1;
    if (match) {
      caseId = match[1];
      caseVersion = Number(match[2]);
    }

    let contextHtml = "";
    let reviewContext = null;

    if (caseId) {
      try {
        reviewContext = await api(`/api/v2/cases/${caseId}/review-context`);
        if (reviewContext) {
          const reasonsList = (reviewContext.reasons || []).map(r => `<li><code>${esc(r)}</code></li>`).join("");
          const rulesList = (reviewContext.triggered_rules || []).map(r => `<li>Rule ID: <code>${esc(r)}</code></li>`).join("");
          
          contextHtml = `
            <div class="panel" style="margin-top:12px; padding:12px; border-left:4px solid var(--amber);">
              <h3>Bối cảnh Hồ sơ & Quy tắc bị chặn</h3>
              <p>Mã hồ sơ: <b>${esc(caseId)}</b> (Phiên bản: ${caseVersion})</p>
              <ul>
                ${reasonsList || "<li>Không tìm thấy lý do chặn cụ thể.</li>"}
              </ul>
              ${rulesList ? `<h4>Quy tắc kích hoạt:</h4><ul>${rulesList}</ul>` : ""}
            </div>
          `;
        }
      } catch (err) {
        contextHtml = `<div class="notice danger">Không tải được chi tiết bối cảnh: ${esc(err.message)}</div>`;
      }
    }

    // Determine current specialist role to prefill
    const currentEmp = $("employee").value;
    let reviewType = "legal_specialist";
    if (currentEmp.includes("CREDIT")) reviewType = "credit_specialist";
    if (currentEmp.includes("INSURANCE")) reviewType = "insurance_specialist";

    $("specDetailPanel").innerHTML = `
      <h2>Chi tiết nhiệm vụ Chuyên viên</h2>

      <div class="notice success" style="margin-top:10px;">
        <h3 style="margin:0 0 6px 0;">${esc(item.title)}</h3>
        <p style="margin:2px 0">Khách hàng: <b>${esc(item.customer_id)}</b></p>
        <p style="margin:2px 0">Độ ưu tiên: <b>${item.priority_score} điểm</b> · Band P${item.priority_band}</p>
      </div>

      ${contextHtml}

      <div class="panel" style="margin-top:12px; padding:16px;">
        <h3>Đưa ra quyết định phê duyệt chuyên môn</h3>
        <p class="muted">Ý kiến của bạn sẽ được lưu vào hồ sơ audit trail của case.</p>
        
        <label class="field" style="margin-top:10px;">Quyết định
          <select id="specDecision" style="margin-top:6px;">
            <option value="cleared">Cleared · Thông qua / giải tỏa block</option>
            <option value="blocked">Blocked · Từ chối hồ sơ</option>
            <option value="needs_more_information">Needs More Info · Yêu cầu bổ sung hồ sơ</option>
          </select>
        </label>

        <label class="field" style="margin-top:10px;">Ý kiến tổng hợp / Lý do
          <textarea id="specSummary" rows="3" style="margin-top:6px;" placeholder="Nhập lý do chi tiết cho quyết định của bạn..."></textarea>
        </label>

        <label class="field" style="margin-top:10px;">Findings (mỗi dòng một ý kiến)
          <textarea id="specFindings" rows="2" style="margin-top:6px;" placeholder="Findings cụ thể..."></textarea>
        </label>

        <div id="infoGapInput" class="hidden" style="margin-top:10px;">
          <label class="field">Tên tài liệu / thông tin thiếu (phân cách bằng dấu phẩy)
            <input id="specRequiredInfo" style="margin-top:6px;" placeholder="financial_statements, ubo_status">
          </label>
        </div>

        <button class="button primary" style="margin-top:16px; width:100%;" onclick="execSpecAction('${caseId}', ${caseVersion}, '${taskId}', '${reviewType}')">
          Gửi quyết định phê duyệt
        </button>
      </div>

      <div id="specActionLog" style="margin-top:10px;"></div>
    `;

    $("specDecision").onchange = (e) => {
      $("infoGapInput").classList.toggle("hidden", e.target.value !== "needs_more_information");
    };
  } catch (error) {
    toast(`Lỗi khi xem chi tiết task: ${esc(error.message)}`, "error");
  }
}

async function execSpecAction(caseId, caseVersion, taskId, reviewType) {
  const logEl = $("specActionLog");
  const decision = $("specDecision").value;
  const summary = $("specSummary").value.trim();
  const rawFindings = $("specFindings").value.split("\n").map(x => x.trim()).filter(Boolean);
  const findings = rawFindings.map(msg => ({
    code: "SPEC_FINDING",
    severity: "low",
    message: msg
  }));
  const requiredInfo = $("specRequiredInfo") ? $("specRequiredInfo").value.split(",").map(x => x.trim()).filter(Boolean) : [];

  if (!summary) {
    return toast("Vui lòng nhập ý kiến tổng hợp.", "warning");
  }

  if (logEl) logEl.innerHTML = `<div class="notice warning">Đang gửi quyết định phê duyệt...</div>`;

  try {
    const payload = {
      review_type: reviewType,
      decision: decision,
      summary: summary,
      findings: findings,
      evidence_ids: reviewType === "legal_specialist" ? ["RULE-CREDIT-UBO-001"] : [], 
      required_information: requiredInfo,
      expected_case_version: caseVersion
    };

    const res = await api(`/api/v2/cases/${caseId}/specialist-reviews`, {
      method: "POST",
      body: JSON.stringify(payload)
    });

    if (logEl) logEl.innerHTML = `
      <div class="notice success">
        <b>✓ Gửi phê duyệt thành công</b><br>
        Quyết định: <code>${esc(decision.toUpperCase())}</code><br>
        Hồ sơ: <code>${esc(caseId)}</code><br>
        <small>Quyết định đã ghi nhận vào audit trail.</small>
      </div>
    `;
    toast(`Đã gửi quyết định phê duyệt cho case ${esc(caseId)}.`, "success");
    await loadSpecialistQueue();
  } catch (error) {
    if (logEl) logEl.innerHTML = `<div class="notice danger"><b>Lỗi thực thi:</b> ${esc(error.message)}</div>`;
    toast(`Lỗi gửi phê duyệt: ${esc(error.message)}`, "error");
  }
}

async function loadManagerWorkload() {
  try {
    const data = await api("/api/v2/me/team/workload");
    $("mgrBlockedCases").textContent = data.aggregate_metrics.blocked_cases;
    $("mgrSlaRisks").textContent = data.aggregate_metrics.sla_risks;
    $("mgrCohortSize").textContent = data.cohort_size;

    const summary = data.aggregate_metrics.ai_recommendation_utilization;
    const container = $("mgrUtilizationSummary");
    
    if (!summary.cohort_minimum_size_met) {
      container.innerHTML = `
        <div class="notice danger">
          <b>RỦI RO BẢO MẬT: Quy mô cohort nhỏ (${data.cohort_size} thành viên).</b><br>
          Manager Console đã kích hoạt cơ chế ẩn thông tin thói quen để bảo vệ RM. Yêu cầu tối thiểu 5 thành viên để xem báo cáo thống kê.
        </div>
      `;
    } else {
      const accepted = summary.utilization_summary.accepted || 0;
      const rejected = summary.utilization_summary.rejected || 0;
      const total = accepted + rejected;
      const pct = total > 0 ? Math.round((accepted / total) * 100) : 100;
      
      container.innerHTML = `
        <div class="notice success">
          Tỷ lệ tương tác AI: <b>${pct}%</b> chấp nhận gợi ý (${accepted} Accepted, ${rejected} Rejected).
        </div>
      `;
    }
  } catch (error) {
    toast(`Lỗi tải dữ liệu Manager: ${esc(error.message)}`, "error");
  }
}

async function updatePersonalizationSettings() {
  try {
    const enabled = $("togglePersonalization").checked;
    const defaultTab = $("prefDefaultTab").value;
    const emailTemp = $("prefEmailTemplate").value;

    // 1. Save preferences via PATCH (correct method)
    await api("/api/v2/me/preferences", {
      method: "PATCH",
      body: JSON.stringify({
        default_case_view: defaultTab,
        preferred_email_template: emailTemp,
        show_evidence_expanded: true
      })
    });

    // 2. Enable/disable via dedicated endpoints
    const consentEndpoint = enabled
      ? "/api/v2/me/personalization/enable"
      : "/api/v2/me/personalization/disable";
    await api(consentEndpoint, {
      method: "POST",
      body: JSON.stringify({
        activity_learning_enabled: enabled,
        allowed_event_categories: ["ui_preferences", "recommendation_feedback"],
        consent_version: "v1"
      })
    });

    toast("Đã cập nhật tùy chọn cá nhân hóa thành công.", "success");
  } catch (error) {
    toast(`Lỗi cập nhật tùy chọn: ${esc(error.message)}`, "error");
  }
}

// Full habit list loading and display
async function loadHabits() {
  const el = $("habitsPanel");
  if (!el) return;
  try {
    const data = await api("/api/v2/me/habits");
    const habits = data.habits || data || [];
    if (!habits.length) {
      el.innerHTML = '<p class="muted" style="font-size:12px;">Chưa có thói quen nào được học.</p>';
      return;
    }
    el.innerHTML = habits.map(h => `
      <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:12px;">
        <div style="flex:1">
          <b>${esc(h.habit_type || h.type || "habit")}</b>
          <span class="chip" style="font-size:9px;margin-left:4px;">${esc(h.status)}</span>
          <small style="display:block;color:var(--muted);">${esc(typeof h.value_json === "object" ? JSON.stringify(h.value_json) : h.value_json || "—")}</small>
        </div>
        ${h.status === "candidate" ? `
          <button onclick="confirmHabit('${h.habit_id}')" class="button secondary" style="padding:2px 6px;font-size:10px;">✓</button>
          <button onclick="rejectHabit('${h.habit_id}')" class="button ghost" style="padding:2px 6px;font-size:10px;color:var(--danger);">✗</button>
        ` : `<button onclick="deleteHabit('${h.habit_id}')" class="button ghost" style="padding:2px 6px;font-size:10px;color:var(--muted);">🗑</button>`}
      </div>
    `).join("");
  } catch(e) {
    el.innerHTML = '<p class="muted" style="font-size:12px;">Không tải được thói quen.</p>';
  }
}

async function confirmHabit(habitId) {
  try {
    await api(`/api/v2/me/habits/${habitId}/confirm`, { method: "POST",
      body: JSON.stringify({ recommendation_id: `REC-${habitId}`, feedback: "accepted" }) });
    toast("Đã xác nhận thói quen.", "success");
    await loadHabits();
  } catch(error) { toast(`Lỗi xác nhận thói quen: ${esc(error.message)}`, "error"); }
}

async function rejectHabit(habitId) {
  try {
    await api(`/api/v2/me/habits/${habitId}/reject`, { method: "POST",
      body: JSON.stringify({ recommendation_id: `REC-${habitId}`, feedback: "rejected" }) });
    toast("Đã từ chối gợi ý thói quen.", "warning");
    await loadHabits();
  } catch(error) { toast(`Lỗi từ chối thói quen: ${esc(error.message)}`, "error"); }
}

async function deleteHabit(habitId) {
  try {
    await api(`/api/v2/me/habits/${habitId}`, { method: "DELETE" });
    toast("Đã xóa thói quen cá nhân hóa.");
    await loadHabits();
  } catch(error) { toast(`Không xóa được thói quen: ${esc(error.message)}`, "warning"); }
}

async function logPersonalizationFeedback(feedbackType) {
  try {
    const data = await api("/api/v2/me/work-queue");
    if (data.queue && data.queue.length) {
      const firstTask = data.queue[0];
      // Use correct path: /me/habits/{habit_id}/confirm
      await api(`/api/v2/me/habits/${firstTask.work_item_id}/confirm`, {
        method: "POST",
        body: JSON.stringify({
          recommendation_id: `REC-${firstTask.work_item_id}`,
          feedback: feedbackType
        })
      });
    }
  } catch (e) {
    console.warn("Feedback log skipped:", e.message);
  }
}

async function deletePersonalizationHabit() {
  try {
    // Load actual habits first, then delete the first one
    const data = await api("/api/v2/me/habits");
    const habits = data.habits || data || [];
    if (!habits.length) { toast("Không có thói quen nào để xóa.", "warning"); return; }
    await api(`/api/v2/me/habits/${habits[0].habit_id}`, { method: "DELETE" });
    toast("Đã xóa thói quen cá nhân hóa. Trải nghiệm quay về mặc định.");
    await loadHabits();
  } catch (error) {
    toast(`Không có thói quen hoạt động để xóa: ${esc(error.message)}`, "warning");
  }
}

function switchControlTab(tabName) {
  const normalized = ["evidence", "ai", "audit", "json"].includes(tabName) ? tabName : "evidence";
  document.querySelectorAll(".control-panel .tab").forEach(button => {
    button.classList.toggle("active", button.dataset.tab === normalized);
  });
  ["Evidence", "Ai", "Audit", "Json"].forEach(name => {
    const panel = $("tab" + name);
    if (panel) panel.classList.toggle("hidden", name.toLowerCase() !== normalized);
  });
}

function bindWorkspaceEvents() {
  $("refreshCases").onclick = loadCases;
  $("createCase").onclick = createCase;

  $("chooseFiles").onclick = () => $("fileInput").click();
  $("fileInput").onchange = event => {
    ui.pendingFiles = Array.from(event.target.files || []);
    renderPendingFiles();
  };
  $("backToInput").onclick = () => setStage(1);
  $("uploadDocuments").onclick = uploadDocuments;
  $("processDocuments").onclick = processDocuments;
  $("addMoreDocuments").onclick = () => {
    setStage(2);
    $("intakePanel").scrollIntoView({behavior:"smooth", block:"start"});
  };
  $("saveCorrection").onclick = () => {
    const field = $("correctionField").value;
    const value = parseCorrection(field, $("correctionValue").value.trim());
    patchProfile(field, value);
  };
  $("confirmProfile").onclick = confirmProfile;
  $("runAnalysis").onclick = runAnalysis;

  const dropzone = $("dropzone");
  dropzone.ondragover = event => {
    event.preventDefault();
    dropzone.classList.add("drag");
  };
  dropzone.ondragleave = () => dropzone.classList.remove("drag");
  dropzone.ondrop = event => {
    event.preventDefault();
    dropzone.classList.remove("drag");
    ui.pendingFiles = Array.from(event.dataTransfer?.files || []);
    renderPendingFiles();
  };

  document.querySelectorAll("#stepper button").forEach(button => {
    button.onclick = () => setStage(Number(button.dataset.step));
  });
  document.querySelectorAll(".control-panel .tab").forEach(button => {
    button.onclick = () => switchControlTab(button.dataset.tab);
  });
  $("session").onchange = async () => {
    await loadEmployeeContext();
    await loadCases();
  };
  $("customerSubmit").onclick = submitCustomerIntake;
  $("creditRequestForm").onsubmit = submitCreditRequest;
  $("customerChooseFiles").onclick = () => $("customerFileInput").click();
  $("customerFileInput").onchange = event => {
    customerUi.pendingFiles = Array.from(event.target.files || []);
    renderCustomerPendingFiles();
  };
  $("customerUpload").onclick = uploadCustomerDocuments;
}

// Bind SSO switcher event
$("loginForm").onsubmit = login;
$("customerRegistrationForm").onsubmit = registerCustomerUser;
$("showCustomerRegistration").onclick = () => showCustomerRegistration(true);
$("showLogin").onclick = () => showCustomerRegistration(false);
$("logoutButton").onclick = logout;

// Role hint under the login role picker
const loginRoleHints = {
  customer: "Cổng khách hàng: gửi yêu cầu tín dụng, theo dõi tiến độ hồ sơ.",
  staff: "Nhân viên ngân hàng: tạo lại hồ sơ cho khách và thẩm định tín dụng (1 người).",
  manager: "Người phê duyệt cuối: chịu trách nhiệm giải ngân và xuất tờ trình.",
};
function syncLoginCustomerVisibility() {
  const isCustomer = $("loginRole")?.value === "customer";
  const wrap = $("loginCustomerWrap");
  if (wrap) wrap.style.display = isCustomer ? "block" : "none";
}
function updateLoginRoleHint() {
  const hint = $("loginRoleHint");
  if (hint) hint.textContent = loginRoleHints[$("loginRole")?.value] || "";
}
if ($("loginRole")) {
  $("loginRole").onchange = () => { syncLoginCustomerVisibility(); updateLoginRoleHint(); };
  syncLoginCustomerVisibility();
  updateLoginRoleHint();
  loadLoginCustomerUsers();
  loadSessionCompanies();
}

// Bind Personalization preferences change
$("togglePersonalization").onchange = updatePersonalizationSettings;
$("prefDefaultTab").onchange = updatePersonalizationSettings;
$("prefEmailTemplate").onchange = updatePersonalizationSettings;
$("btnDeleteHabit").onclick = deletePersonalizationHabit;
bindWorkspaceEvents();

setStage(1);
setIntakeStatus("draft");
// rmWorkspace là khối hiển thị mặc định trong HTML — ẩn hết ngay khi boot
// để không lộ UI nhân viên trước khi biết role thật từ /me/context.
hideAllWorkspaces();
if (authToken) {
  $("loginScreen").style.display = "none";
  loadEmployeeContext().then(() => loadCases());
}

