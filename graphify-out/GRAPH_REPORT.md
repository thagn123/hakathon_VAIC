# Graph Report - c:/Users/Admin/Desktop/SHB  (2026-07-25)

## Corpus Check
- Large corpus: 555 files · ~549,009 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 5747 nodes · 12740 edges · 278 communities (233 shown, 45 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1367 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- V2 Repository & Storage Core
- API v2 Routers & Endpoints
- Multi-Agent Orchestration
- Credit Decisioning & Eligibility
- Web Frontend Dashboard
- Personalization & Work Optimization
- Enterprise Integration & SQLite
- Risk Gate & Evidence Validation
- Data Schemas & Evaluation
- Module Component 9
- Module Component 10
- Module Component 11
- Module Component 12
- Module Component 13
- Module Component 14
- Module Component 15
- Module Component 16
- Module Component 17
- Module Component 18
- Module Component 19
- Module Component 20
- Module Component 21
- Module Component 22
- Module Component 23
- Module Component 24
- Module Component 25
- Module Component 26
- Module Component 27
- Module Component 28
- Module Component 29
- Module Component 30
- Module Component 31
- Module Component 32
- Module Component 33
- Module Component 34
- Module Component 35
- Module Component 36
- Module Component 37
- Module Component 38
- Module Component 39
- Module Component 40
- Module Component 41
- Module Component 42
- Module Component 43
- Module Component 44
- Module Component 45
- Module Component 46
- Module Component 47
- Module Component 48
- Module Component 49
- Module Component 50
- Module Component 51
- Module Component 52
- Module Component 53
- Module Component 54
- Module Component 55
- Module Component 56
- Module Component 57
- Module Component 58
- Module Component 59
- Module Component 60
- Module Component 61
- Module Component 62
- Module Component 63
- Module Component 64
- Module Component 65
- Module Component 66
- Module Component 67
- Module Component 68
- Module Component 69
- Module Component 70
- Module Component 71
- Module Component 72
- Module Component 73
- Module Component 74
- Module Component 75
- Module Component 76
- Module Component 77
- Module Component 78
- Module Component 79
- Module Component 80
- Module Component 81
- Module Component 82
- Module Component 83
- Module Component 84
- Module Component 85
- Module Component 86
- Module Component 87
- Module Component 88
- Module Component 89
- Module Component 90
- Module Component 91
- Module Component 92
- Module Component 93
- Module Component 94
- Module Component 95
- Module Component 96
- Module Component 97
- Module Component 98
- Module Component 99
- Module Component 100
- Module Component 101
- Module Component 102
- Module Component 103
- Module Component 104
- Module Component 105
- Module Component 106
- Module Component 107
- Module Component 108
- Module Component 109
- Module Component 110
- Module Component 111
- Module Component 112
- Module Component 113
- Module Component 114
- Module Component 115
- Module Component 116
- Module Component 117
- Module Component 118
- Module Component 119
- Module Component 120
- Module Component 121
- Module Component 122
- Module Component 123
- Module Component 124
- Module Component 125
- Module Component 126
- Module Component 127
- Module Component 128
- Module Component 129
- Module Component 130
- Module Component 131
- Module Component 132
- Module Component 133
- Module Component 134
- Module Component 135
- Module Component 136
- Module Component 137
- Module Component 138
- Module Component 139
- Module Component 140
- Module Component 141
- Module Component 142
- Module Component 143
- Module Component 144
- Module Component 145
- Module Component 146
- Module Component 147
- Module Component 148
- Module Component 149
- Module Component 150
- Module Component 151
- Module Component 152
- Module Component 153
- Module Component 154
- Module Component 155
- Module Component 156
- Module Component 157
- Module Component 158
- Module Component 159
- Module Component 160
- Module Component 161
- Module Component 162
- Module Component 163
- Module Component 164
- Module Component 165
- Module Component 166
- Module Component 167
- Module Component 168
- Module Component 169
- Module Component 170
- Module Component 171
- Module Component 172
- Module Component 173
- Module Component 174
- Module Component 175
- Module Component 176
- Module Component 177
- Module Component 178
- Module Component 179
- Module Component 180
- Module Component 181
- Module Component 182
- Module Component 183
- Module Component 184
- Module Component 185
- Module Component 186
- Module Component 187
- Module Component 188
- Module Component 189
- Module Component 190
- Module Component 191
- Module Component 192
- Module Component 193
- Module Component 194
- Module Component 195
- Module Component 196
- Module Component 197
- Module Component 198
- Module Component 199
- Module Component 200
- Module Component 201
- Module Component 202
- Module Component 203
- Module Component 204
- Module Component 205
- Module Component 206
- Module Component 207
- Module Component 208
- Module Component 209
- Module Component 210
- Module Component 211
- Module Component 212
- Module Component 213
- Module Component 214
- Module Component 215
- Module Component 216
- Module Component 217
- Module Component 218
- Module Component 219
- Module Component 220
- Module Component 221
- Module Component 222
- Module Component 223
- Module Component 224
- Module Component 225
- Module Component 226
- Module Component 227
- Module Component 228
- Module Component 229
- Module Component 230
- Module Component 231
- Module Component 232
- Module Component 233
- Module Component 234
- Module Component 235
- Module Component 236
- Module Component 237
- Module Component 238
- Module Component 239
- Module Component 240
- Module Component 245
- Module Component 246
- Module Component 247
- Module Component 248
- Module Component 249
- Module Component 250
- Module Component 251
- Module Component 255
- Module Component 262
- Module Component 263
- Module Component 264
- Module Component 265

## God Nodes (most connected - your core abstractions)
1. `V2Repository` - 126 edges
2. `PersistentHybridIndex` - 115 edges
3. `KnowledgeChunk` - 92 edges
4. `LocalEmbedding` - 91 edges
5. `LegalKnowledgeService` - 84 edges
6. `esc()` - 76 edges
7. `ControlledRetrievalOrchestrator` - 70 edges
8. `UpstreamTimeoutError` - 60 edges
9. `V2WorkflowEngine` - 60 edges
10. `UpstreamUnavailableError` - 59 edges

## Surprising Connections (you probably didn't know these)
- `FakeIndex` --uses--> `ExecutionDenied`  [INFERRED]
  tests/unit/test_v2_evidence_validator.py → app/actions/executor.py
- `FakeIndex` --uses--> `ActionExecutorV2`  [INFERRED]
  tests/unit/test_v2_evidence_validator.py → app/actions/executor.py
- `CaseRunResult` --uses--> `EligibilityEngine`  [INFERRED]
  benchmarks/run.py → app/eligibility/engine.py
- `MockProductService` --uses--> `EligibilityEngine`  [INFERRED]
  tests/e2e/test_v3_golden_cases.py → app/eligibility/engine.py
- `MockProductService` --uses--> `EligibilityEngine`  [INFERRED]
  tests/e2e/test_v3_specialist_review_closure.py → app/eligibility/engine.py

## Import Cycles
- None detected.

## Communities (278 total, 45 thin omitted)

### Community 0 - "V2 Repository & Storage Core"
Cohesion: 0.05
Nodes (128): agentMeta(), akDomainLabel, api(), applyIntake(), appraiseCreditRequest(), approveAction(), baselineMapping, bindWorkspaceEvents() (+120 more)

### Community 1 - "API v2 Routers & Endpoints"
Cohesion: 0.04
Nodes (70): BaseModel, RAG_PROVIDER (local|mcp|hybrid) is the source of truth.      RAG_MCP_ENABLED i, _resolve_rag_provider(), Settings, load_source_card(), Path, ValueError, Data Source Card validation gate used before publishing serving artifacts. (+62 more)

### Community 2 - "Multi-Agent Orchestration"
Cohesion: 0.05
Nodes (87): Concrete per-agent RetrievalPolicy instances -- RAG & Guardrail Implementation, AgentType, ControlledRetrievalResult, GroundingItem, MetadataRef, MissingInformation, BaseModel, Enum (+79 more)

### Community 3 - "Credit Decisioning & Eligibility"
Cohesion: 0.12
Nodes (87): ActionExecutorV2, ExecutionDenied, PermissionError, Exact-payload, evidence-gated and idempotent mock executor., ApproveBody, ConfirmProfileBody, ContextCorrectionBody, CreateCaseBody (+79 more)

### Community 4 - "Web Frontend Dashboard"
Cohesion: 0.05
Nodes (77): _crm_adapter(), _default_assembler(), _iam_adapter(), CRM/IAM/SSO come from PostgreSQL when DATABASE_URL is set (pilot/prod),     els, _sso_adapter(), _is_expired(), datetime, ResolvedValue (+69 more)

### Community 5 - "Personalization & Work Optimization"
Cohesion: 0.04
Nodes (74): detect_slot_conflicts(), Conflict detection MVP -- RAG & Guardrail Implementation Plan Phase 2 section 1, Group the given chunks by (product_id, section_path); any group with     more t, PersistentHybridIndex, All chunks currently in this index, newest-insertion-order not         guarante, Exact Structured Lookup (Phase 1 / prompt section 4): a request         that al, Hierarchical Parent-Child Retrieval (Phase 3 section 26): given         a retri, Return every indexed chunk for a (document_id[, document_version]).          U (+66 more)

### Community 6 - "Enterprise Integration & SQLite"
Cohesion: 0.05
Nodes (71): LegalKnowledgeService, EmbeddingProvider, Path, Ingest V3 synthetic banking policy documents (banking_policy_documents.json)., Legal RAG supports evidence/explanation; it never owns eligibility outcome., EventObserver, InMemoryObservabilityRecorder, Any (+63 more)

### Community 7 - "Risk Gate & Evidence Validation"
Cohesion: 0.06
Nodes (63): APIRouter, create_router(), V3 Rule Registry adapter: translates V3 blueprint rule schema to the runtime El, Registry backed by V3 blueprint rule schema.      Does NOT call require_servin, V3RuleRegistry, map_enterprise_role_to_role_type(), extraction_quality(), ocr_pdf_sections() (+55 more)

### Community 8 - "Data Schemas & Evaluation"
Cohesion: 0.08
Nodes (48): BaseExpertRuntime, Provider adapter shared by expert runtimes.  LLM output is optional enrichment, AgentManifest, AgentRunMetadata, AgentType, ArtifactRef, ConfidenceBreakdown, EvidenceReference (+40 more)

### Community 9 - "Module Component 9"
Cohesion: 0.06
Nodes (67): _blocking_rule_evaluations(), Any, Full rule-evaluation dicts (not just IDs) for every blocking rule in     the gi, ComplexityRouter, SharedCaseState, plan_v2/09_WORKFLOW_ORCHESTRATION.md section 5: complex if multi-intent,     cr, _evidence(), SharedCaseState (+59 more)

### Community 10 - "Module Component 10"
Cohesion: 0.03
Nodes (74): ApprovalPreview, ApprovalTokenResponse, action, approvalToken, caseId, description, expiresAt, hashCode (+66 more)

### Community 11 - "Module Component 11"
Cohesion: 0.03
Nodes (74): action, branchStatusCounts, businessNeed, caseId, caseNumber, checklist, companyId, companyName (+66 more)

### Community 12 - "Module Component 12"
Cohesion: 0.04
Nodes (74): required, required, required, required, required, agent_manifest_version, agent_type, case_id (+66 more)

### Community 13 - "Module Component 13"
Cohesion: 0.06
Nodes (31): Signed approvals bound to case, approver, permissions and exact payload hash., Canonical example payloads for the V2 contracts.  These are the single source, Json(), _canonical(), _json_dict(), Any, SharedCaseState, Cases belonging to any customer in customer_ids, regardless of         owning e (+23 more)

### Community 14 - "Module Component 14"
Cohesion: 0.06
Nodes (55): CustomerResolver, Any, Enum, str, Customer Resolver and Evidence Inventory loader.  Implements Phase 2 of the SH, Mock method for retrieving previously verified documents/facts., Determines customer status and loads any existing profile/evidence., ResolutionResult (+47 more)

### Community 15 - "Module Component 15"
Cohesion: 0.08
Nodes (66): delete_my_habit(), _employee_iam_adapter(), _employee_sso_adapter(), _error(), get_case_review_context(), get_case_specialist_reviews(), get_my_personalization(), get_my_preferences() (+58 more)

### Community 16 - "Module Component 16"
Cohesion: 0.07
Nodes (61): _configure_pytesseract(), is_ocr_available(), ocr_pdf_bytes(), OcrUnavailableError, Any, RuntimeError, OCR fallback for scanned/image PDFs where app/knowledge/parsers.py's pypdf-base, Cheap capability probe (no PDF rasterization) for a health-check or     a UI ba (+53 more)

### Community 17 - "Module Component 17"
Cohesion: 0.04
Nodes (37): agent_service_suggestions(), get_next_best_work(), get_task_status_in_db(), json_loads_safe(), Any, Connection, Next Best Work Engine.   Performs 2-stage task prioritization: 1. Hard Eligib, Map task title → bank services RM can fill into the case suggestion.      Pref (+29 more)

### Community 18 - "Module Component 18"
Cohesion: 0.07
Nodes (42): load_v3_rules(), Path, EligibilityEngine, Any, Fail-closed deterministic rule execution; no LLM is allowed to decide pass/fail., EligibilityRule, LegalSummary, ProductEligibility (+34 more)

### Community 19 - "Module Component 19"
Cohesion: 0.09
Nodes (57): classify_document(), detect_needs(), detect_pain_points(), extract_document_fields(), _find_location(), fold_text(), _integer(), _money() (+49 more)

### Community 20 - "Module Component 20"
Cohesion: 0.04
Nodes (60): items, type, uniqueItems, const, $ref, properties, type, items (+52 more)

### Community 21 - "Module Component 21"
Cohesion: 0.07
Nodes (47): _jaccard(), mmr_select(), MMR diversity selection -- RAG & Guardrail Implementation Plan Phase 3 section, lambda_relevance closer to 1.0 favors relevance, closer to 0.0     favors novel, _tokenize(), FusedCandidate, FusionMode, FusionStrategy (+39 more)

### Community 22 - "Module Component 22"
Cohesion: 0.10
Nodes (33): AssistanceRequest, CollaborationSession, ConstraintNotice, ExpertFinding, SynthesisResult, CoordinationResult, CoordinatorAgent, Any (+25 more)

### Community 23 - "Module Component 23"
Cohesion: 0.05
Nodes (52): CaseDetailController, EmployeeWorkspaceController, ApprovalScreen, _ApprovalScreenState, initState, LoginScreen, _LoginScreenState, CaseDetailScreen (+44 more)

### Community 24 - "Module Component 24"
Cohesion: 0.04
Nodes (51): items, maxItems, type, items, type, items, type, items (+43 more)

### Community 25 - "Module Component 25"
Cohesion: 0.09
Nodes (35): RagMCPSettings, CallerPrincipal, ExpertSearchRequest, Search filters exposed to an Expert Agent; domain is fixed by its MCP endpoint., ScopedSearchFilters, SearchFilters, SearchKnowledgeRequest, authorize_tool() (+27 more)

### Community 26 - "Module Component 26"
Cohesion: 0.09
Nodes (21): Deterministic credit-domain services used by the Credit Expert., Any, Sync bridge for the sync credit router. Returns ``None`` to fall back., ServiceAdvisoryRuntime, CreditReadinessService, Any, Credit readiness analysis without making an approval decision.  The service de, Create a transparent recommendation; never make the final decision. (+13 more)

### Community 27 - "Module Component 27"
Cohesion: 0.04
Nodes (46): data_label, dataset_name, files, legal/banking_policy_documents.json, legal/eligibility_rules.json, operations/sop_workflow.json, products/product_catalog.json, scenarios/conversations.json (+38 more)

### Community 28 - "Module Component 28"
Cohesion: 0.05
Nodes (45): properties, items, minItems, type, items, type, items, type (+37 more)

### Community 29 - "Module Component 29"
Cohesion: 0.04
Nodes (45): type, type, properties, type, format, type, minimum, type (+37 more)

### Community 30 - "Module Component 30"
Cohesion: 0.06
Nodes (43): _ApprovalForm, _Check, _ConfirmRow, _SummaryCell, _TimelineRow, _ActionCenter, _ActionRow, _Body (+35 more)

### Community 31 - "Module Component 31"
Cohesion: 0.14
Nodes (25): AssessmentStatus, DocumentAssuranceService, Any, str, Evaluates a document through the 3-gate assurance pipeline., Case-scoped document intake and customer profile builder., _event(), IntakeService (+17 more)

### Community 32 - "Module Component 32"
Cohesion: 0.08
Nodes (30): LocalEmbedding, Deterministic, key-free embedding for offline/dev/test and reproducible CI., EmbeddingProvider, Path, ReferenceLibraryService, OperationsKnowledgeService, EmbeddingProvider, Path (+22 more)

### Community 33 - "Module Component 33"
Cohesion: 0.05
Nodes (42): type, type, type, type, properties, maximum, minimum, type (+34 more)

### Community 34 - "Module Component 34"
Cohesion: 0.06
Nodes (31): CachedGeminiEmbedding, IndexNamespace, MetadataFilterReason, namespace_mismatch(), Enum, Path, str, Identity of one PersistentHybridIndex's dense vector space -- Phase 2     "Inde (+23 more)

### Community 35 - "Module Component 35"
Cohesion: 0.09
Nodes (39): action_input_schema(), action_output_schema(), contracts_dir(), _find_contracts_dir(), load_schema(), load_tool_contracts(), Any, Path (+31 more)

### Community 36 - "Module Component 36"
Cohesion: 0.10
Nodes (18): connect(), _PgCompatCursor, _PgConn, Any, Cursor, PostgreSQL / SQLite connection helpers for the V2 state store.  Provides trans, SQLite uses ? placeholders; psycopg2 uses %s., Cursor wrapper for sqlite3 to provide RealDictCursor ergonomics and     Json co (+10 more)

### Community 37 - "Module Component 37"
Cohesion: 0.13
Nodes (24): _hash(), Any, SharedCaseState, Start a new analysis run while preserving case, context and user-safe history., A human specialist (Legal/Product) has resolved every reason the         risk g, Persist a sanitized decision record without raw prompts, PII or secrets., force_route ("simple"|"complex") bypasses ComplexityRouter for         evaluati, V2WorkflowEngine (+16 more)

### Community 38 - "Module Component 38"
Cohesion: 0.07
Nodes (41): type, type, $ref, format, type, type, type, type (+33 more)

### Community 39 - "Module Component 39"
Cohesion: 0.10
Nodes (31): _clean_conversation(), build_conflict(), decision_impact_for(), _hashable(), ResolvedValue, Conflict detection between context sources.  plan_v2/04_EMPLOYEE_WORKSPACE_CON, None if all candidates agree (or fewer than 2 candidates were given)., _clean_state() (+23 more)

### Community 40 - "Module Component 40"
Cohesion: 0.05
Nodes (39): AppColors, background, blue, blue100, darkTheme, error, gold, gold100 (+31 more)

### Community 41 - "Module Component 41"
Cohesion: 0.05
Nodes (40): $ref, type, type, type, type, properties, $ref, type (+32 more)

### Community 42 - "Module Component 42"
Cohesion: 0.12
Nodes (21): ClientSession, Any, RagMCPClient, Small official-SDK client used by an orchestrator or smoke test., AgentCapabilityResponse, CitationVerificationRequest, CitationVerificationResponse, ExpertListSourcesRequest (+13 more)

### Community 43 - "Module Component 43"
Cohesion: 0.05
Nodes (39): type, $ref, type, type, type, $ref, type, minimum (+31 more)

### Community 44 - "Module Component 44"
Cohesion: 0.12
Nodes (32): ContextSnapshot, IntentResult, select_clarification(), calibrated_confidence(), ResolvedValue, IntentExtractor, Any, DeterministicIntentExtractor (+24 more)

### Community 45 - "Module Component 45"
Cohesion: 0.05
Nodes (38): enum, type, format, type, type, type, minimum, type (+30 more)

### Community 46 - "Module Component 46"
Cohesion: 0.07
Nodes (38): type, format, type, type, type, type, type, null (+30 more)

### Community 47 - "Module Component 47"
Cohesion: 0.06
Nodes (36): ChangeNotifier, Color color,, int open, ready,, CaseController, bg, _Body, build, c (+28 more)

### Community 48 - "Module Component 48"
Cohesion: 0.07
Nodes (37): type, format, type, type, maximum, minimum, type, type (+29 more)

### Community 49 - "Module Component 49"
Cohesion: 0.06
Nodes (32): api_client.dart, api_config.dart, bool get, CaseDetail?, CaseDetail? get, controllers/case_controller.dart, dart:convert, ApiClient (+24 more)

### Community 50 - "Module Component 50"
Cohesion: 0.16
Nodes (33): ErrorResponse, get_my_context(), get_my_habits(), BaseModel, Assembles the complete Employee Context Snapshot with Provenance mapping., RecommendationFeedbackBody, AuthorizationContext, ConsentModel (+25 more)

### Community 51 - "Module Component 51"
Cohesion: 0.06
Nodes (36): properties, enum, maximum, minimum, type, enum, maximum, minimum (+28 more)

### Community 52 - "Module Component 52"
Cohesion: 0.10
Nodes (24): Context, CachedGeminiEmbedding, CachedOpenAIEmbedding, cosine(), create_embedding_provider(), EmbeddingProvider, fold(), LocalEmbedding (+16 more)

### Community 53 - "Module Component 53"
Cohesion: 0.06
Nodes (34): ../../design/widgets/nav_sidebar.dart, action, build, caseId, checked, _commitments, createState, detail (+26 more)

### Community 54 - "Module Component 54"
Cohesion: 0.06
Nodes (33): documentMetadata, type, type, type, additionalProperties, properties, type, maximum (+25 more)

### Community 55 - "Module Component 55"
Cohesion: 0.06
Nodes (33): default, items, type, default, description, items, type, default (+25 more)

### Community 56 - "Module Component 56"
Cohesion: 0.13
Nodes (28): AgentType, Enum, str, Query Router -- RAG & Guardrail Implementation Plan Phase 3 section 22.  Pure, RetrievalStrategy, route_query(), _detect_entities(), _detect_language() (+20 more)

### Community 57 - "Module Component 57"
Cohesion: 0.12
Nodes (30): abstention_correct(), aggregate_optional_floats(), citation_coverage(), citation_validity(), forbidden_product_violation(), legal_flag_recall(), missing_information_recall(), product_precision() (+22 more)

### Community 58 - "Module Component 58"
Cohesion: 0.06
Nodes (32): items, type, uniqueItems, properties, items, maxItems, type, maximum (+24 more)

### Community 59 - "Module Component 59"
Cohesion: 0.06
Nodes (30): case_models.dart, OpportunityCard, _OpportunityCard, attrs, _branchStatusCounts, ctx, customer, _customerName (+22 more)

### Community 60 - "Module Component 60"
Cohesion: 0.07
Nodes (28): core/controllers/employee_workspace_controller.dart, design/design.dart, ../../design/theme/app_theme.dart, features/approval/approval_screen.dart, features/auth/login_screen.dart, features/case_detail/case_detail_screen.dart, features/credit_requests/credit_requests_screen.dart, features/employee_workspace/employee_workspace_screen.dart (+20 more)

### Community 61 - "Module Component 61"
Cohesion: 0.07
Nodes (29): Color, ../../core/models/employee_models.dart, IconData, build, caption, color, controller, createState (+21 more)

### Community 62 - "Module Component 62"
Cohesion: 0.27
Nodes (28): _base_chunk(), _credit_pack(), IngestionError, _legal_pack(), _markdown_chunks(), _markdown_sections(), _operations_pack(), _product_pack() (+20 more)

### Community 63 - "Module Component 63"
Cohesion: 0.11
Nodes (21): minimize_for_llm(), Any, ContextSnapshot, plan_v2/04_EMPLOYEE_WORKSPACE_CONTEXT.md section 6: structured summary     only, plan_v2/04_EMPLOYEE_WORKSPACE_CONTEXT.md section 3 sequence.          Raises a, IntentExtractionError, ContextSnapshot, IntentResult (+13 more)

### Community 64 - "Module Component 64"
Cohesion: 0.07
Nodes (29): properties, items, type, minimum, type, type, enum, type (+21 more)

### Community 65 - "Module Component 65"
Cohesion: 0.10
Nodes (29): properties, type, type, format, type, format, type, type (+21 more)

### Community 66 - "Module Component 66"
Cohesion: 0.09
Nodes (29): required, required, access_scope, active, content_hash, document_id, document_type, document_version (+21 more)

### Community 67 - "Module Component 67"
Cohesion: 0.11
Nodes (22): CRMPort, _CacheEntry, CircuitBreaker, CircuitOpenError, CircuitState, Enum, Exception, RuntimeError (+14 more)

### Community 68 - "Module Component 68"
Cohesion: 0.07
Nodes (28): type, enum, additionalProperties, properties, type, constraintNotice, type, format (+20 more)

### Community 69 - "Module Component 69"
Cohesion: 0.10
Nodes (28): type, type, type, type, type, properties, format, type (+20 more)

### Community 70 - "Module Component 70"
Cohesion: 0.08
Nodes (28): additionalProperties, properties, type, type, type, type, format, type (+20 more)

### Community 71 - "Module Component 71"
Cohesion: 0.07
Nodes (27): CaseTaskDraft, ChecklistItem, ContextSnapshot, EligibilityIssue, EligibilityResult, IntentResult, ProductBundle, ProductFeeLimit (+19 more)

### Community 72 - "Module Component 72"
Cohesion: 0.12
Nodes (22): client(), _create_body(), Any, SharedCaseState, TestClient, HTTP-driven tests for the Agent Knowledge Console (app/api/v2/employee_router.py, There is no request field that lets a Legal Specialist target the     Product A, _repo() (+14 more)

### Community 73 - "Module Component 73"
Cohesion: 0.16
Nodes (16): ExecutionPlan, NextBestAction, NextBestQuestion, PlanStep, BaseModel, Deterministic Planner, Next Best Question and Next Best Action contracts., End-to-end synthetic V2 analysis workflow with safe partial resume., NextBestService (+8 more)

### Community 74 - "Module Component 74"
Cohesion: 0.08
Nodes (25): AuthorizationContext, AuthorizationContext, customerScope, employee_models, employeeId, enabled, excludedActions, fromJson (+17 more)

### Community 75 - "Module Component 75"
Cohesion: 0.08
Nodes (26): type, $ref, $ref, type, $ref, items, maxItems, type (+18 more)

### Community 76 - "Module Component 76"
Cohesion: 0.08
Nodes (26): type, type, evidenceRef, type, type, additionalProperties, properties, required (+18 more)

### Community 77 - "Module Component 77"
Cohesion: 0.16
Nodes (7): _ClosingConnection, Any, Connection, Path, RagStore, Persistent SQLite repository owned exclusively by the RAG MCP service., Atomically publish a fully validated corpus; old serving data survives any failu

### Community 78 - "Module Component 78"
Cohesion: 0.08
Nodes (25): @freezed, ApprovalPayload, ApprovalResult, ChecklistItem, EvidenceRef, ApprovalResult, ProductSearchResult, _ApprovalResult (+17 more)

### Community 79 - "Module Component 79"
Cohesion: 0.16
Nodes (16): Any, ContextSnapshot, IntentResult, ResolvedValue, Deterministic intent fallback used offline and after model failure., extract_amount(), extract_tenor_months(), fold_text() (+8 more)

### Community 80 - "Module Component 80"
Cohesion: 0.08
Nodes (23): backend_adapter, _backendProducts, bundle, evidence, finalStatus, map, mapDetail, mapQueue (+15 more)

### Community 81 - "Module Component 81"
Cohesion: 0.12
Nodes (16): deterministic_matching_reason(), deterministic_semantic_score(), GemmaClient, get_gemma_client(), injection_semantic_judge(), LLMClientError, Any, Exception (+8 more)

### Community 82 - "Module Component 82"
Cohesion: 0.08
Nodes (23): additionalProperties, type, additionalProperties, type, additionalProperties, type, $defs, agentRun (+15 more)

### Community 83 - "Module Component 83"
Cohesion: 0.08
Nodes (24): type, additionalProperties, type, type, items, type, uniqueItems, maximum (+16 more)

### Community 84 - "Module Component 84"
Cohesion: 0.21
Nodes (22): _apply_bank_credit_records(), appraise_credit_request(), _can_view(), create_credit_request(), _customer_view(), decide_credit_request(), _error(), forward_credit_request() (+14 more)

### Community 85 - "Module Component 85"
Cohesion: 0.17
Nodes (14): CacheKey, Any, Retrieval cache -- RAG & Guardrail Implementation Plan Phase 3 section 30.  I, Called when a snapshot/policy/catalog/SOP version changes --         drops ever, RetrievalCache, _key(), Phase 3 section 30: cache key composition must isolate cross-customer requests, test_different_case_id_is_never_a_cache_hit_for_the_others_entry() (+6 more)

### Community 86 - "Module Component 86"
Cohesion: 0.09
Nodes (23): items, minItems, type, enum, type, type, type, properties (+15 more)

### Community 87 - "Module Component 87"
Cohesion: 0.09
Nodes (23): type, type, default, type, properties, type, approval_reference, approved (+15 more)

### Community 88 - "Module Component 88"
Cohesion: 0.09
Nodes (23): items, type, type, additionalProperties, properties, required, chunk_id, candidates (+15 more)

### Community 89 - "Module Component 89"
Cohesion: 0.14
Nodes (19): Any, Return validated semantic enrichment or ``None`` on degradation.          The, GuardrailViolation, Any, ValueError, Domain Guardrails for AI agents.  Enforces strict boundary rules for specific, Reject persistence of private reasoning-shaped fields recursively.      Concis, Product Agent:     - Must not fabricate fees, rates, limits, approval.     - M (+11 more)

### Community 90 - "Module Component 90"
Cohesion: 0.23
Nodes (19): date, Validate one claim's citation against the controlled source index.      Determ, validate_claim(), _chunk(), FakeIndex, date, Tests for the real evidence validator (app.safety.evidence_validator), which re, Minimal stand-in for PersistentHybridIndex.get_chunks_for_document. (+11 more)

### Community 91 - "Module Component 91"
Cohesion: 0.13
Nodes (20): init_employee_db(), Initialize employee tables and seed mock data., client(), _create_working_capital_case(), isolated_db(), TestClient, End-to-end regression test driving the specialist-review action surface through, Acceptance criterion (P0, per code-review response #4): all eight     fields ap (+12 more)

### Community 92 - "Module Component 92"
Cohesion: 0.09
Nodes (21): FloatingActionButton?, appBar, body, build, center, _DesktopLayout, _DesktopThreeCol, endDrawer (+13 more)

### Community 93 - "Module Component 93"
Cohesion: 0.10
Nodes (22): format, type, items, type, items, type, additionalProperties, required (+14 more)

### Community 94 - "Module Component 94"
Cohesion: 0.09
Nodes (21): additionalProperties, $id, access, decision_role, lifecycle_status, owner, schema_version, source_id (+13 more)

### Community 95 - "Module Component 95"
Cohesion: 0.09
Nodes (22): type, type, properties, type, type, type, type, claim (+14 more)

### Community 96 - "Module Component 96"
Cohesion: 0.09
Nodes (22): approved, blocked, completed, expired, failed, not_required, pending, planned (+14 more)

### Community 97 - "Module Component 97"
Cohesion: 0.19
Nodes (20): create_agent_knowledge_entry(), _domain_for(), get_agent_activity(), _knowledge_service_for(), list_agent_knowledge(), AgentDomain, Agent cua toi dang lam gi": knowledge entries this domain's Agent     can retri, _to_knowledge_record() (+12 more)

### Community 98 - "Module Component 98"
Cohesion: 0.19
Nodes (13): content_hash(), dedup_key(), OperationsService, Any, Path, Create versioned, deduplicated drafts without external side effects., prepare(), Draft, checklist and dedup acceptance tests. (+5 more)

### Community 99 - "Module Component 99"
Cohesion: 0.10
Nodes (20): api, context, currentEmployeeId, error, isAuthenticated, isLoading, isManager, kDemoPersonas (+12 more)

### Community 100 - "Module Component 100"
Cohesion: 0.10
Nodes (21): items, minItems, type, items, type, type, allowed_uses, prohibited_uses (+13 more)

### Community 101 - "Module Component 101"
Cohesion: 0.11
Nodes (21): items, items, type, items, minItems, type, additionalProperties, properties (+13 more)

### Community 102 - "Module Component 102"
Cohesion: 0.10
Nodes (21): sourceMetadata, allowed_uses, business_owner, data_steward, decision_role, lifecycle_status, max_age_seconds, prohibited_uses (+13 more)

### Community 103 - "Module Component 103"
Cohesion: 0.23
Nodes (6): Governed RAG MCP server for product, legal and operations knowledge., ChunkCitation, RetrievedChunk, Any, date, RagKnowledgeService

### Community 104 - "Module Component 104"
Cohesion: 0.21
Nodes (19): Access, AccessMethod, DataDomain, DataTier, DecisionRole, Freshness, Governance, Identifiers (+11 more)

### Community 105 - "Module Component 105"
Cohesion: 0.17
Nodes (16): V2 domain models mirroring plan_v2/contracts/*.json (schema_version 2.0.0).  C, ActionInput, ActionOutput, load_tool_registry(), BaseModel, Enum, str, Pydantic mirror of plan_v2/contracts/tool_contracts.json.  Unlike the other th (+8 more)

### Community 106 - "Module Component 106"
Cohesion: 0.18
Nodes (18): average(), forbidden_retrieved(), ndcg_at_k(), no_result_correct(), rate(), Pure retrieval-quality metric calculators -- RAG & Guardrail Implementation Pla, For 'no_relevant_result'/'empty_query' ground-truth cases (relevant     == []):, recall_at_k() (+10 more)

### Community 107 - "Module Component 107"
Cohesion: 0.10
Nodes (20): additionalProperties, properties, required, type, ALLOW_WITH_WARNING, BLOCK_DECISION, FAIL_CLOSED, MANUAL_REVIEW (+12 more)

### Community 108 - "Module Component 108"
Cohesion: 0.10
Nodes (20): required, agent_manifest_version, case_id, fallback_used, output_schema_version, prompt_version, revision, started_at (+12 more)

### Community 109 - "Module Component 109"
Cohesion: 0.15
Nodes (12): CircuitBreaker, compute_health(), ProviderHealth, Minimal 3-state (CLOSED/OPEN/HALF_OPEN) circuit breaker.      ``clock`` is inj, True if a caller may attempt the guarded (MCP) call right now., Non-invasive status snapshot for /api/v2/health -- does not itself         make, Cheap (no I/O) health snapshot shared by RagProviderRouter.health()     and cal, Path (+4 more)

### Community 110 - "Module Component 110"
Cohesion: 0.11
Nodes (19): additionalProperties, required, type, type, minLength, type, properties, access (+11 more)

### Community 111 - "Module Component 111"
Cohesion: 0.11
Nodes (19): maximum, minimum, type, type, format, type, null, string (+11 more)

### Community 112 - "Module Component 112"
Cohesion: 0.11
Nodes (19): retrievalMetadata, effective_at, latency_ms, task_id, trace_id, additionalProperties, required, type (+11 more)

### Community 113 - "Module Component 113"
Cohesion: 0.29
Nodes (18): client(), create_payroll_case(), headers(), TestClient, HTTP acceptance tests for the V2 RM vertical slice., test_complete_analysis_preview_approval_execute_journey(), test_context_correction_records_provenance_and_invalidates_approval(), test_context_resolve_sanitizes_pii_without_creating_case() (+10 more)

### Community 114 - "Module Component 114"
Cohesion: 0.17
Nodes (13): canonical_hash(), Any, Return a stable, prefix-free SHA-256 used by collaboration contracts., InsuranceReadinessService, Any, Insurance coverage readiness analysis without binding, pricing or approving a p, _assess_findings_quality(), Any (+5 more)

### Community 115 - "Module Component 115"
Cohesion: 0.16
Nodes (17): bm25_scores(), Same normalization as tokens(), but preserves term frequency (a     set collaps, Real Okapi BM25 -- Phase 1 / prompt section 6: "Không được giả vờ     hash-vect, token_list(), _chunk(), Phase 1 section 6: real BM25 sparse retrieval, not the pre-existing naive token, BM25's term-frequency component saturates (diminishing returns),     but a docu, A term appearing in only 1 of 10 documents (rare, high IDF) must     score its (+9 more)

### Community 116 - "Module Component 116"
Cohesion: 0.18
Nodes (13): ProductKnowledgeService, Any, Return governed catalog metadata used for policy filters.          Alternative, End-to-end proof that V2WorkflowEngine._product_evidence no longer     accepts, test_tampered_product_quote_is_caught_by_the_live_engine_wiring(), Acceptance and leakage tests for the persistent product RAG., service(), test_acl_filter_is_applied_before_serving_context() (+5 more)

### Community 117 - "Module Component 117"
Cohesion: 0.17
Nodes (13): ClaimInput, detect_conflicts(), EvidenceValidationResult, EvidenceValidator, _normalize(), Enum, str, Deterministic, independent evidence/citation validation.  Replaces the previou (+5 more)

### Community 118 - "Module Component 118"
Cohesion: 0.15
Nodes (15): impacted_nodes(), Map changed artifacts to earliest safe resume nodes., _find_endpoint_by_name(), Regression tests for the CONTEXT_CORRECTION_POLICIES registry (app/workflow/imp, Preserves pre-existing behavior for change tokens that are NOT a     customer.a, Preserves pre-existing behavior for the /resume endpoint's     document-driven, app/api/v2/router.py must not keep its own separate field list --     inspect t, Guards the other direction: a field added to the registry without     also bein (+7 more)

### Community 119 - "Module Component 119"
Cohesion: 0.27
Nodes (17): aggregate_bools(), _blocking_rule_ids(), build_report(), _expected(), _git_state(), main(), _now_iso(), Any (+9 more)

### Community 120 - "Module Component 120"
Cohesion: 0.11
Nodes (18): additionalProperties, type, type, properties, type, items, type, uniqueItems (+10 more)

### Community 121 - "Module Component 121"
Cohesion: 0.11
Nodes (18): additionalProperties, required, type, ACTIVE, approved, residency, retention, sensitivity (+10 more)

### Community 122 - "Module Component 122"
Cohesion: 0.11
Nodes (17): additionalProperties, type, additionalProperties, type, additionalProperties, type, $defs, agentRunMetadata (+9 more)

### Community 123 - "Module Component 123"
Cohesion: 0.11
Nodes (17): additionalProperties, $id, case_id, schema_version, trace_id, workflow, required, $schema (+9 more)

### Community 124 - "Module Component 124"
Cohesion: 0.11
Nodes (18): items, type, $ref, maximum, minimum, type, evidences, loop_count (+10 more)

### Community 125 - "Module Component 125"
Cohesion: 0.21
Nodes (15): RagProviderRouter, Routes a retrieval call through RAG_PROVIDER=local|mcp|hybrid.      - ``local`, Tests for app.knowledge.rag_provider: circuit breaker, local/mcp/hybrid routing, test_hybrid_mode_does_not_fall_back_on_non_recoverable_error(), test_hybrid_mode_falls_back_to_local_on_recoverable_error(), test_hybrid_mode_opens_circuit_after_threshold_and_then_skips_mcp_entirely(), test_hybrid_mode_prefers_mcp_when_healthy(), test_hybrid_mode_requires_mcp_search_callable() (+7 more)

### Community 126 - "Module Component 126"
Cohesion: 0.12
Nodes (16): Breakpoints, build, desktop, getScreenSize, gridColumns, isDesktop, isMobile, mobile (+8 more)

### Community 127 - "Module Component 127"
Cohesion: 0.18
Nodes (15): mcp_common - Shared schemas, config, and LLM client for all MCP servers., ApprovalToken, ApproveCaseRequest, CreateCaseRequest, EvidenceItem, OperationsResult, Pydantic schemas mirroring V3 Data Blueprint contracts for MCP mesh., Operations Agent output contract. (+7 more)

### Community 128 - "Module Component 128"
Cohesion: 0.12
Nodes (17): minLength, type, minLength, type, additionalProperties, properties, type, pattern (+9 more)

### Community 129 - "Module Component 129"
Cohesion: 0.12
Nodes (17): $ref, additionalProperties, type, properties, type, items, type, confirmed_facts (+9 more)

### Community 130 - "Module Component 130"
Cohesion: 0.12
Nodes (16): additionalProperties, $defs, resolvedValue, $id, confidence, confirmed, source_id, additionalProperties (+8 more)

### Community 131 - "Module Component 131"
Cohesion: 0.19
Nodes (14): login(), LoginRequest, LoginResponse, BaseModel, Local login endpoint for the dashboard demo., _sso_adapter(), enforce_token_identity(), Fail-closed guard for every /api/v2 route in this router.      LOGIC: Đầu tiên (+6 more)

### Community 132 - "Module Component 132"
Cohesion: 0.13
Nodes (14): additionalProperties, $id, customer, employee, schema_version, workspace, required, $schema (+6 more)

### Community 133 - "Module Component 133"
Cohesion: 0.13
Nodes (15): enum, type, customer, document, employee, workspace, domain, credit (+7 more)

### Community 134 - "Module Component 134"
Cohesion: 0.13
Nodes (15): type, last_report_reference, publish_gate, quality, required_checks, type, additionalProperties, properties (+7 more)

### Community 135 - "Module Component 135"
Cohesion: 0.13
Nodes (15): required, agent_type, claim_id, evidence_coverage, evidence_refs, finding_id, support_status, claim_text_sanitized (+7 more)

### Community 136 - "Module Component 136"
Cohesion: 0.13
Nodes (15): message_id, text, type, message_id, received_at, request, text, format (+7 more)

### Community 137 - "Module Component 137"
Cohesion: 0.19
Nodes (12): MetadataEnvelope, MetadataEvent, MetadataRef, MetadataRelation, BaseModel, Metadata Plane Foundation - Core Models (P0.1)  Provides a unified metadata st, Pointer to another object in the system., Relation between this object and another (e.g. DERIVED_FROM, RENEWS). (+4 more)

### Community 138 - "Module Component 138"
Cohesion: 0.23
Nodes (11): check_output_language(), LanguageGuardrailResult, Output language guardrail -- RAG & Guardrail Implementation Plan Phase 4 sectio, Not an auto-rewrite (no LLM call site to actually rewrite text     safely witho, suggest_safe_rewrite_markers(), Phase 4 section 39: forbidden overclaim phrases in Agent output text., test_approval_language_is_flagged(), test_multiple_forbidden_phrases_are_all_reported() (+3 more)

### Community 139 - "Module Component 139"
Cohesion: 0.14
Nodes (14): type, additionalProperties, properties, required, type, items, type, type (+6 more)

### Community 140 - "Module Component 140"
Cohesion: 0.14
Nodes (14): type, type, additionalProperties, properties, required, type, gold_location, ingestion_job (+6 more)

### Community 141 - "Module Component 141"
Cohesion: 0.19
Nodes (10): GroundingStatus, GroundingValidator, Any, BaseModel, Enum, str, Grounding Validator for P0.3 Trust Foundation.  Ensures that any generated Evi, Validates citations against the true underlying sources. (+2 more)

### Community 142 - "Module Component 142"
Cohesion: 0.26
Nodes (11): expand_query(), expanded_query_text(), ExpansionTerm, Query Expansion -- RAG & Guardrail Implementation Plan Phase 3 section 23. Vers, Case-insensitive substring match against the registry above. Returns     an emp, Convenience: original query + all matched expansion terms appended,     for cal, Phase 3 section 23: versioned synonym expansion with provenance., test_expanded_query_text_appends_synonyms() (+3 more)

### Community 144 - "Module Component 144"
Cohesion: 0.26
Nodes (11): DocumentScanResult, InjectionSpan, Prompt injection scanner for RETRIEVED DOCUMENT content -- RAG & Guardrail Impl, Splits on sentence-like boundaries (same convention as     app/knowledge/compre, scan_chunk_text(), Phase 4 section 34: retrieved-document prompt injection scanning., test_empty_text_is_not_flagged(), test_injected_instruction_is_flagged_even_amid_legitimate_content() (+3 more)

### Community 145 - "Module Component 145"
Cohesion: 0.15
Nodes (11): _brand, build, current, _footnote, _item, NavSidebar, _sectionLabel, package:go_router/go_router.dart (+3 more)

### Community 146 - "Module Component 146"
Cohesion: 0.15
Nodes (13): type, type, type, business_owner, data_steward, additionalProperties, properties, required (+5 more)

### Community 147 - "Module Component 147"
Cohesion: 0.15
Nodes (13): missing_information, schema_version, required, ambiguities, entities, evidence_spans, field_confidence, overall_confidence (+5 more)

### Community 148 - "Module Component 148"
Cohesion: 0.15
Nodes (13): $defs, evidence, additionalProperties, required, type, claim_id, claim, is_valid (+5 more)

### Community 149 - "Module Component 149"
Cohesion: 0.23
Nodes (10): FakeClock, Injectable monotonic clock so circuit-breaker tests never sleep()., test_circuit_half_open_failure_reopens_circuit(), test_circuit_half_open_limits_concurrent_probe_calls(), test_circuit_half_open_success_closes_circuit(), test_circuit_open_blocks_until_cooldown_elapses(), test_circuit_opens_after_failure_threshold_consecutive_failures(), test_circuit_starts_closed_and_allows_requests() (+2 more)

### Community 150 - "Module Component 150"
Cohesion: 0.26
Nodes (12): _between(), _branch_behavior(), _bullets(), _category_for(), main(), _parse_products(), Path, Convert the SHB Corporate RAG Product Manual (.odt) into the canonical product (+4 more)

### Community 151 - "Module Component 151"
Cohesion: 0.30
Nodes (9): main(), Any, Path, Executable security and reliability evaluation suites., run_all(), run_reliability(), run_security(), Security/reliability datasets and quality gates. (+1 more)

### Community 152 - "Module Component 152"
Cohesion: 0.18
Nodes (9): EmployeeIdentity, IAMPort, _json_loads(), PermissionGrant, Any, Protocol, TypedDict, psycopg2 decodes JSONB columns to Python objects already; SQLite     stored the (+1 more)

### Community 153 - "Module Component 153"
Cohesion: 0.17
Nodes (11): core/rm_workspace_core.dart, EdgeInsetsGeometry?, build, label, padding, showIcon, status, StatusBadge (+3 more)

### Community 154 - "Module Component 154"
Cohesion: 0.17
Nodes (12): required, latency_ms, output_schema_version, prompt_version, tool_policy_version, tools_called, denied_tools, manifest_version (+4 more)

### Community 155 - "Module Component 155"
Cohesion: 0.17
Nodes (7): Phase 1 section 8: per-agent retrieval policy data. This tests the POLICY DATA, docs/RAG_GUARDRAIL_REQUIREMENT_EXTRACTION.md section 2: Legal     "Không được t, docs/RAG_GUARDRAIL_REQUIREMENT_EXTRACTION.md section 2: Product's     allowed s, None of the three agents are allowed to retrieve "model inference"     as if it, test_legal_policy_is_fail_closed_and_exact_lookup_first(), test_no_agent_policy_allows_model_inference_as_a_source(), test_product_policy_allows_unverified_customer_data_labelled_clearly()

### Community 156 - "Module Component 156"
Cohesion: 0.25
Nodes (9): Clarification, Select at most one clarification with the highest decision value., Ambiguity, EvidenceSpan, IntentResult, BaseModel, Enum, Pydantic mirror of plan_v2/contracts/intent_result.schema.json. (+1 more)

### Community 157 - "Module Component 157"
Cohesion: 0.29
Nodes (9): compress_chunk_text(), CompressedSpan, Contextual compression -- RAG & Guardrail Implementation Plan Phase 3 section 2, Splits on sentence-like boundaries (also '|', this corpus's own     field separ, Phase 3 section 29: extractive compression preserves exact offsets into the ORI, test_compressed_spans_are_substrings_of_the_original_text_at_their_offsets(), test_empty_text_returns_no_spans(), test_sentence_with_exception_marker_and_date_is_kept_over_generic_marketing_text() (+1 more)

### Community 158 - "Module Component 158"
Cohesion: 0.27
Nodes (11): CaseStatus, ConfidenceSource, DataTier, IntentType, Enum, str, V3 Data tier classification., V3 Intent types from blueprint §5.1. (+3 more)

### Community 159 - "Module Component 159"
Cohesion: 0.18
Nodes (11): document, workflow, workspace, enum, cache, conversation_confirmed, crm, iam (+3 more)

### Community 160 - "Module Component 160"
Cohesion: 0.18
Nodes (11): required, task, dedup_key, owner, status, task_id, task_type, additionalProperties (+3 more)

### Community 161 - "Module Component 161"
Cohesion: 0.18
Nodes (7): Tests for benchmarks/run.py: dataset integrity, end-to-end execution of a few r, A provider-level failure must show up as status="infra_error", not as     a qua, test_cost_is_never_fabricated(), test_infra_error_is_recorded_not_silently_treated_as_zero_recall(), test_non_security_case_runs_end_to_end_with_deterministic_intent(), test_score_case_marks_infra_error_distinctly_from_a_quality_miss(), test_security_case_is_blocked_at_input_not_run_through_engine()

### Community 162 - "Module Component 162"
Cohesion: 0.18
Nodes (10): background_color, description, display, icons, name, orientation, prefer_related_applications, short_name (+2 more)

### Community 163 - "Module Component 163"
Cohesion: 0.29
Nodes (7): main(), Any, Path, Reproducible deterministic evaluation for intent, retrieval and eligibility., run_evaluation(), Evaluation dataset and quality gates are executable in CI., test_offline_quality_gates()

### Community 164 - "Module Component 164"
Cohesion: 0.29
Nodes (4): RuntimeError, T, RagProviderUnavailableError, Raised by mode="mcp" (never falls back) when the MCP call fails.

### Community 165 - "Module Component 165"
Cohesion: 0.24
Nodes (8): ExpertAgentType, FastMCP, create_server(), _new_mcp(), ProfileTokenMiddleware, Any, Authenticate a single MCP profile without exposing credentials in tool arguments, tools_for()

### Community 166 - "Module Component 166"
Cohesion: 0.24
Nodes (10): enum, agentType, enum, issued_by, CreditExpert, EvidenceValidator, InsuranceExpert, LegalExpert (+2 more)

### Community 167 - "Module Component 167"
Cohesion: 0.20
Nodes (10): additionalProperties, required, type, confidence, evidence_coverage, consistency_status, freshness_status, input_completeness (+2 more)

### Community 168 - "Module Component 168"
Cohesion: 0.20
Nodes (10): enum, type, method, API, DATABASE, DOCUMENT_UPLOAD, EVENT, FILE (+2 more)

### Community 169 - "Module Component 169"
Cohesion: 0.28
Nodes (7): FreshnessPolicy, datetime, Enum, str, TTL/staleness policy per context layer.  plan_v2/04_EMPLOYEE_WORKSPACE_CONTEXT, Matches plan_v2/contracts/data_source_card.schema.json#/properties/freshness/sta, StaleBehavior

### Community 170 - "Module Component 170"
Cohesion: 0.28
Nodes (7): CircuitState, Citation, GroundingPack, BaseModel, Enum, str, RAG provider routing: local / mcp / hybrid, with a circuit breaker and controll

### Community 171 - "Module Component 171"
Cohesion: 0.22
Nodes (5): Any, V2 Audit Logger for SHB Corporate Sales Copilot.  Implements Phase 10 of the E, Log an automated or human decision., Log a specialist overriding a system risk/policy block., V2EventLogger

### Community 172 - "Module Component 172"
Cohesion: 0.22
Nodes (8): canonical_product_id_namespace, corpus_id, data_mode, dataset_version, generated_at, publish_policy, schema_version, sources

### Community 173 - "Module Component 173"
Cohesion: 0.22
Nodes (9): additionalProperties, required, type, stale, customer, attributes, customer_id, profile_version (+1 more)

### Community 174 - "Module Component 174"
Cohesion: 0.22
Nodes (9): additionalProperties, required, type, access_scope, employee, employee_id, organization_unit, permissions (+1 more)

### Community 175 - "Module Component 175"
Cohesion: 0.22
Nodes (9): A_INTERNAL, A_OFFICIAL, B_LICENSED, C_OPEN, D_DERIVED, E_SYNTHETIC, tier, enum (+1 more)

### Community 176 - "Module Component 176"
Cohesion: 0.22
Nodes (9): recommended_action, enum, ask_clarification, call_context_tool, continue_workflow, defer_missing_field, escalate_human, reject_out_of_scope (+1 more)

### Community 177 - "Module Component 177"
Cohesion: 0.50
Nodes (8): _legal_orchestrator(), Phase 2 section 4/17: ControlledRetrievalOrchestrator must actually call the in, _request(), test_grounding_pack_content_hash_is_deterministic(), test_orchestrator_diagnostics_report_real_candidate_counts(), test_orchestrator_executes_exact_sparse_dense_and_hybrid_channels(), test_orchestrator_returns_ok_with_a_populated_grounding_pack(), test_unknown_agent_type_is_a_configuration_error_not_a_crash()

### Community 178 - "Module Component 178"
Cohesion: 0.33
Nodes (5): DownCRM, Runtime adapter reliability tests., test_open_circuit_surfaces_standard_fail_closed_error(), test_transient_read_timeout_is_retried_safely(), TransientCRM

### Community 179 - "Module Component 179"
Cohesion: 0.29
Nodes (4): RateLimitedWarningLogger, Logs a WARNING at most once per ``cooldown_seconds`` per event key.      Repea, Logger, test_rate_limited_logger_reset_allows_immediate_warning_again()

### Community 180 - "Module Component 180"
Cohesion: 0.32
Nodes (5): Any, Keys always include access scope, preventing cross-user cache reuse., ScopedTTLCache, Hashable, test_cache_is_isolated_by_scope_and_version()

### Community 181 - "Module Component 181"
Cohesion: 0.25
Nodes (8): additionalProperties, required, type, conversation, confirmed_facts, current_goal, open_questions, rejected_assumptions

### Community 182 - "Module Component 182"
Cohesion: 0.25
Nodes (8): enum, type, AUTHORITATIVE, DISCOVERY, ENRICHMENT, EVALUATION_ONLY, VERIFICATION, decision_role

### Community 183 - "Module Component 183"
Cohesion: 0.25
Nodes (8): enum, authorityTier, A_INTERNAL, A_OFFICIAL, B_LICENSED, C_OPEN, D_DERIVED, E_SYNTHETIC

### Community 184 - "Module Component 184"
Cohesion: 0.25
Nodes (8): workflow, additionalProperties, required, type, current_node, loop_count, tasks, workflow_version

### Community 185 - "Module Component 185"
Cohesion: 0.38
Nodes (4): Any, SharedCaseState, payload_hash(), Any

### Community 188 - "Module Component 188"
Cohesion: 0.29
Nodes (5): ChunkIndex, EvidenceLike, Protocol, The subset of PersistentHybridIndex this module depends on., SemanticSimilarityCheck

### Community 189 - "Module Component 189"
Cohesion: 0.33
Nodes (5): SharedCaseState, Submission Readiness Service.  Implements Phase 8 of the SHB Corporate Sales C, Evaluates whether the case is ready for submission., ReadinessResult, SubmitReadinessService

### Community 190 - "Module Component 190"
Cohesion: 0.29
Nodes (7): expired, enum, invalid, needs_review, processing, uploaded, verified

### Community 191 - "Module Component 191"
Cohesion: 0.29
Nodes (7): enum, decisionRole, AUTHORITATIVE, DISCOVERY, ENRICHMENT, EVALUATION_ONLY, VERIFICATION

### Community 192 - "Module Component 192"
Cohesion: 0.33
Nodes (4): compile_catalog(), main(), Administrative CLI kept outside the LLM-visible MCP tool allowlist., Environment-only configuration for the independent RAG MCP service.

### Community 193 - "Module Component 193"
Cohesion: 0.33
Nodes (5): core/api_client.dart, core/api_config.dart, core/controllers/case_controller.dart, core/mock/mock_loader.dart, core/models/case_models.dart

### Community 194 - "Module Component 194"
Cohesion: 0.33
Nodes (6): session_id, workspace, additionalProperties, required, type, current_screen

### Community 195 - "Module Component 195"
Cohesion: 0.33
Nodes (6): maximum, minimum, type, additionalProperties, type, field_confidence

### Community 196 - "Module Component 196"
Cohesion: 0.33
Nodes (6): enum, high, low, medium, none, decision_impact

### Community 197 - "Module Component 197"
Cohesion: 0.33
Nodes (6): additionalProperties, required, type, accessScope, branches, roles

### Community 198 - "Module Component 198"
Cohesion: 0.33
Nodes (6): ALLOW_WITH_WARNING, BLOCK_DECISION, FAIL_CLOSED, MANUAL_REVIEW, stale_behavior, enum

### Community 199 - "Module Component 199"
Cohesion: 0.27
Nodes (6): minLength, type, case_id, updated_at, format, type

### Community 200 - "Module Component 200"
Cohesion: 0.40
Nodes (5): is_recoverable_error(), True if ``exc`` looks like a transient network/availability failure.      NOT, BaseException, test_generic_runtime_error_is_not_recoverable(), test_network_errors_are_recoverable()

### Community 201 - "Module Component 201"
Cohesion: 0.50
Nodes (4): get_settings(), BaseModel, MCP Common configuration from environment - V3 aligned., Settings

### Community 202 - "Module Component 202"
Cohesion: 0.40
Nodes (5): items, type, uniqueItems, dependencies, type

### Community 203 - "Module Component 203"
Cohesion: 0.50
Nodes (4): _intake_assistance(), Any, ContextSnapshot, Separate database inheritance, product advice, and credit verification.

### Community 205 - "Module Component 205"
Cohesion: 0.50
Nodes (3): Any, date, Path

### Community 207 - "Module Component 207"
Cohesion: 0.50
Nodes (4): $ref, resolved_slots, additionalProperties, type

### Community 208 - "Module Component 208"
Cohesion: 0.50
Nodes (4): default, items, type, constraints

### Community 209 - "Module Component 209"
Cohesion: 0.50
Nodes (4): sub_intents, items, type, uniqueItems

### Community 210 - "Module Component 210"
Cohesion: 0.50
Nodes (4): success_criteria, default, items, type

### Community 212 - "Module Component 212"
Cohesion: 0.67
Nodes (3): @JsonSerializable, _, _

### Community 216 - "Module Component 216"
Cohesion: 0.67
Nodes (3): additionalProperties, type, attributes

## Knowledge Gaps
- **1462 isolated node(s):** `ASSETS`, `statusLabels`, `intentLabels`, `profileLabels`, `ui` (+1457 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LegalKnowledgeService` connect `Enterprise Integration & SQLite` to `Module Component 97`, `API v2 Routers & Endpoints`, `Credit Decisioning & Eligibility`, `Multi-Agent Orchestration`, `Personalization & Work Optimization`, `Module Component 37`, `Risk Gate & Evidence Validation`, `Data Schemas & Evaluation`, `Module Component 73`, `Module Component 42`, `Module Component 106`, `Module Component 109`, `Module Component 15`, `Module Component 177`, `Module Component 50`, `Module Component 119`, `Module Component 25`, `Module Component 125`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `V2Repository` connect `Module Component 13` to `Credit Decisioning & Eligibility`, `Risk Gate & Evidence Validation`, `Module Component 72`, `Module Component 9`, `Module Component 14`, `Module Component 15`, `Module Component 17`, `Module Component 50`, `Module Component 113`, `Module Component 19`, `Module Component 31`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `V2WorkflowEngine` connect `Module Component 37` to `Credit Decisioning & Eligibility`, `Module Component 35`, `Enterprise Integration & SQLite`, `Risk Gate & Evidence Validation`, `Data Schemas & Evaluation`, `Module Component 73`, `Module Component 44`, `Module Component 15`, `Module Component 113`, `Module Component 18`, `Module Component 116`, `Module Component 117`, `Module Component 22`, `Module Component 119`, `Module Component 89`, `Module Component 90`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `V2Repository` (e.g. with `ActionExecutorV2` and `ExecutionDenied`) actually correct?**
  _`V2Repository` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `PersistentHybridIndex` (e.g. with `AuthorityTier` and `VerificationStatus`) actually correct?**
  _`PersistentHybridIndex` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `KnowledgeChunk` (e.g. with `AuthorityTier` and `VerificationStatus`) actually correct?**
  _`KnowledgeChunk` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `LocalEmbedding` (e.g. with `CreditKnowledgeService` and `AuthorityTier`) actually correct?**
  _`LocalEmbedding` has 7 INFERRED edges - model-reasoned connections that need verification._