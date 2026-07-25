# 05_KNOWN_LIMITATIONS

## 1. Demo-scope Limitations
- **Mock Document OCR**: Mock PDF documents generated in E2E tests contain minimal structural text; production deployment will ingest full scanned PDFs via Tesseract/Cloud Vision OCR.
- **Single Synthetic Customer Depth**: "Công ty Cổ phần Thiết bị Minh Phát" (COMP-MP) has full synthetic records across CRM, CIC, and Intake. Other mock customers (COMP-ABC, COMP-XYZ) have standard CRM baseline profiles.

## 2. Architecture Notes
- **Live Collaboration Graph**: Live multi-agent workflow uses ProductExpert, CreditExpert, InsuranceExpert, and PlannerCoordinator (Eligibility check is executed via deterministic EligibilityEngine rule step). `LegalExpert` runtime is retained for legacy compatibility.
- **Credit Safety**: Automated agent outputs do not self-approve or issue unconditional limit commitments. All credit requests return status `NEED_REVIEW` or `CONDITIONAL` for human credit officer appraisal.
