"""Credit readiness analysis without making an approval decision.

The service derives transparent indicators from structured case facts and the
deterministic EligibilityEngine output. It never changes a legal/rule result,
never invents pricing/limits and never approves a loan.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

from app.schemas.v2.credit_request import CorporateCreditRequestCreate


class CreditReadinessService:
    REQUIRED_CREDIT_FACTS = (
        "annual_revenue",
        "operating_years",
        "has_bad_debt_12m",
        "ubo_status",
    )

    def appraise_request(self, request: CorporateCreditRequestCreate) -> Dict[str, Any]:
        """Create a transparent recommendation; never make the final decision."""
        score = 100
        findings: List[str] = []
        cic = request.cic_debt_classification.lower()

        if "nhóm 1" not in cic and "group 1" not in cic:
            score -= 40
            findings.append("CIC không thuộc Nhóm 1.")
        if request.debt_to_equity_ratio > 3:
            score -= 25
            findings.append("Tỷ số D/E lớn hơn 3.")
        if request.net_profit_billion_vnd <= 0:
            score -= 20
            findings.append("Lợi nhuận sau thuế không dương.")

        requested_billion = request.requested_amount_vnd / 1_000_000_000
        if request.request_type in {"loan", "both"} and request.collateral_value_billion_vnd < requested_billion:
            score -= 15
            findings.append("Giá trị tài sản bảo đảm thấp hơn số tiền đề nghị.")

        score = max(score, 0)
        recommendation = "recommend" if score >= 80 else "conditional" if score >= 60 else "not_recommended"
        if not findings:
            findings.append("Không phát hiện cảnh báo định lượng từ dữ liệu khách hàng cung cấp.")

        return {
            "score": score,
            "recommendation": recommendation,
            "summary": (
                f"Agent chấm điểm sơ bộ {score}/100 ({recommendation}). "
                + " ".join(findings)
                + " Đây chỉ là khuyến nghị; quyết định giải ngân cuối cùng thuộc Manager."
            ),
        }

    def recommend_services(self, request: CorporateCreditRequestCreate) -> Dict[str, Any]:
        """Second agent pass: cross-sell services for the Credit Specialist queue.

        LLM picks/justifies from a fixed catalog when configured; otherwise the
        deterministic rules below run (allowlist means the LLM can't invent a
        product beyond these).
        """
        from app.credit.service_advisory_llm import ServiceAdvisoryRuntime

        llm_result = ServiceAdvisoryRuntime().advise({
            "request_type": request.request_type,
            "requested_amount_vnd": float(request.requested_amount_vnd),
            "industry": request.industry,
            "net_revenue_billion_vnd": float(request.net_revenue_billion_vnd),
            "casa_avg_balance_billion_vnd": float(request.casa_avg_balance_billion_vnd),
            "collateral_value_billion_vnd": float(request.collateral_value_billion_vnd),
            "cic_debt_classification": request.cic_debt_classification,
        })
        if llm_result is not None:
            return llm_result

        services: List[Dict[str, Any]] = []
        casa = float(request.casa_avg_balance_billion_vnd)
        revenue = float(request.net_revenue_billion_vnd)
        industry = request.industry.lower()

        if request.request_type in {"loan", "both"}:
            services.append({
                "service": "Vốn lưu động / hạn mức tín dụng",
                "priority": "high",
                "reason": "Khách đề nghị khoản vay; cấu trúc hạn mức giúp linh hoạt giải ngân.",
            })
        if casa < max(revenue * 0.02, 1.0):
            services.append({
                "service": "Gói quản lý dòng tiền / CASA",
                "priority": "high",
                "reason": "Số dư CASA thấp so với doanh thu; cần tăng dòng tiền qua SHB.",
            })
        if any(token in industry for token in ("xuất", "nhập", "export", "import", "thương mại")):
            services.append({
                "service": "LC / Bảo lãnh thanh toán quốc tế",
                "priority": "medium",
                "reason": "Ngành gắn thương mại quốc tế; phù hợp LC và bảo lãnh.",
            })
        if float(request.collateral_value_billion_vnd) > 0:
            services.append({
                "service": "Bảo hiểm tài sản đảm bảo",
                "priority": "medium",
                "reason": "Có TSĐB; nên gắn bảo hiểm để bảo vệ giá trị thế chấp.",
            })
        if request.request_type in {"service", "both"} or not services:
            services.append({
                "service": "Internet Banking doanh nghiệp / chi hộ lương",
                "priority": "low",
                "reason": "Dịch vụ nền tảng giúp giữ quan hệ giao dịch hàng ngày.",
            })

        names = ", ".join(item["service"] for item in services[:3])
        return {
            "services": services,
            "summary": (
                f"[Rule] Agent đề xuất {len(services)} dịch vụ đi kèm (ưu tiên: {names}). "
                "Chỉ là khuyến nghị; RM chọn dịch vụ phù hợp khi bổ sung tờ trình."
            ),
            "source": "rule",
        }

    def analyze(
        self,
        *,
        product_result: Dict[str, Any],
        eligibility_result: Dict[str, Any],
        customer_attributes: Dict[str, Any],
        documents: Iterable[Dict[str, Any]],
        business_snapshot: Optional[Dict[str, Any]] = None,
        requested_amount: Optional[float] = None,
        requested_tenor_months: Optional[int] = None,
        loan_purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        recommendations = list(product_result.get("recommendations", []))
        credit_products = [
            item
            for item in recommendations
            if item.get("credit_flag") is True
            or str(item.get("product_family", item.get("family", ""))).lower() == "credit"
        ]
        if not credit_products:
            return {
                "status": "not_applicable",
                "agent_run_id": f"ARUN-CREDIT-{uuid.uuid4().hex[:8].upper()}",
                "credit_product_ids": [],
                "known_facts": [],
                "missing_information": [],
                "risk_flags": [],
                "hard_blocks": [],
                "structure_draft": None,
                "capacity_indicators": {},
                "conclusion": "Case hiện không có sản phẩm tín dụng để phân tích chuyên sâu.",
                "decision_authority": "credit_officer_and_approval_workflow",
            }

        profile = self._profile(customer_attributes, business_snapshot or {})
        requested_amount = requested_amount or self._number(
            profile.get("requested_amount_vnd"), profile.get("amount_vnd"), profile.get("requested_amount")
        )
        requested_tenor_months = requested_tenor_months or self._integer(
            profile.get("requested_tenor_months"), profile.get("tenor_months")
        )
        loan_purpose = loan_purpose or self._text(profile.get("loan_purpose"), profile.get("purpose"))

        facts = {
            key: profile.get(key)
            for key in self.REQUIRED_CREDIT_FACTS
            if profile.get(key) is not None
        }
        if requested_amount is not None:
            facts["requested_amount"] = requested_amount
        if requested_tenor_months is not None:
            facts["requested_tenor_months"] = requested_tenor_months
        if loan_purpose:
            facts["loan_purpose"] = loan_purpose

        missing = [key for key in self.REQUIRED_CREDIT_FACTS if profile.get(key) is None]
        normalized_documents = {
            str(item.get("document_type")): str(item.get("status")) for item in documents
        }
        if normalized_documents.get("financial_statements") not in {"verified", "valid"}:
            missing.append("financial_statements")

        hard_blocks: List[Dict[str, Any]] = []
        rule_missing: List[str] = []
        relevant_ids = {str(item.get("product_id")) for item in credit_products}
        for product in eligibility_result.get("products", []):
            if str(product.get("product_id")) not in relevant_ids:
                continue
            rule_missing.extend(str(item) for item in product.get("missing_information", []))
            for rule in product.get("rules", []):
                if rule.get("severity") == "blocking" and rule.get("status") in {"failed", "pending_review"}:
                    hard_blocks.append(
                        {
                            "product_id": product.get("product_id"),
                            "rule_id": rule.get("rule_id"),
                            "failure_code": rule.get("failure_code"),
                            "status": rule.get("status"),
                            "human_review_allowed": bool(rule.get("human_review_allowed", False)),
                        }
                    )
        missing = list(dict.fromkeys([*missing, *rule_missing]))

        indicators = self._capacity_indicators(profile, requested_amount)
        revenue = profile.get("annual_revenue")
        if requested_amount is not None and isinstance(revenue, (int, float)) and revenue > 0:
            indicators["requested_amount_to_annual_revenue"] = round(float(requested_amount) / float(revenue), 4)
        else:
            indicators["requested_amount_to_annual_revenue"] = None

        risk_flags: List[Dict[str, Any]] = []
        if profile.get("has_bad_debt_12m") is True:
            risk_flags.append(
                {
                    "code": "BAD_DEBT_12M",
                    "severity": "blocking",
                    "basis": "customer.has_bad_debt_12m=true",
                }
            )
        if not indicators["cash_flow_capacity_assessable"]:
            risk_flags.append(
                {
                    "code": "CASH_FLOW_CAPACITY_NOT_ASSESSABLE",
                    "severity": "information_gap",
                    "basis": "Thiếu EBITDA hoặc nghĩa vụ trả nợ hiện hữu.",
                }
            )
        if missing:
            risk_flags.append(
                {
                    "code": "CREDIT_INPUTS_INCOMPLETE",
                    "severity": "information_gap",
                    "basis": list(missing),
                }
            )

        if hard_blocks:
            status = "hard_block_detected"
            conclusion = "Phát hiện hard block từ Rule Engine; Credit Expert không được cấu trúc khoản vay thành phương án có thể phê duyệt."
        elif missing:
            status = "needs_information"
            conclusion = "Chưa đủ dữ liệu để đánh giá khả năng trả nợ và hoàn thiện cấu trúc tín dụng."
        else:
            status = "ready_for_credit_review"
            conclusion = "Đủ dữ liệu sàng lọc ban đầu; phương án vẫn phải được cán bộ tín dụng thẩm định và phê duyệt theo quy trình."

        dimensions = self._analysis_dimensions(
            profile=profile,
            documents=normalized_documents,
            indicators=indicators,
            hard_blocks=hard_blocks,
            missing=missing,
        )
        confidence = self._confidence(dimensions)
        repayment_sources = self._repayment_sources(profile)
        structure_scenarios = self._structure_scenarios(
            requested_amount=requested_amount,
            requested_tenor_months=requested_tenor_months,
            loan_purpose=loan_purpose,
            repayment_sources=repayment_sources,
            hard_blocks=hard_blocks,
            capacity_assessable=bool(indicators["cash_flow_capacity_assessable"]),
        )

        return {
            "status": status,
            "agent_run_id": f"ARUN-CREDIT-{uuid.uuid4().hex[:8].upper()}",
            "credit_product_ids": sorted(relevant_ids),
            "known_facts": [facts],
            "missing_information": missing,
            "risk_flags": risk_flags,
            "hard_blocks": hard_blocks,
            "capacity_indicators": indicators,
            "analysis_dimensions": dimensions,
            "repayment_sources": repayment_sources,
            "structure_scenarios": structure_scenarios,
            "analysis_confidence": confidence,
            "document_analysis": [
                {"document_type": name, "status": status, "usable_for_decision": status in {"verified", "valid"}}
                for name, status in sorted(normalized_documents.items())
            ],
            "structure_draft": {
                "status": "draft_for_credit_officer_review",
                "requested_amount": requested_amount,
                "requested_tenor_months": requested_tenor_months,
                "loan_purpose": loan_purpose,
                "pricing": None,
                "approved_limit": None,
            },
            "conclusion": conclusion,
            "decision_authority": "credit_officer_and_approval_workflow",
        }

    @staticmethod
    def _profile(customer_attributes: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Merge already-confirmed profile sections without discarding provenance."""

        merged = dict(customer_attributes)
        for section in (
            "company_identity",
            "business_profile",
            "operating_model",
            "transaction_profile",
            "cash_flow_profile",
            "financing_profile",
            "legal_profile",
        ):
            value = snapshot.get(section)
            if isinstance(value, dict):
                merged.update(value)
        return merged

    @staticmethod
    def _number(*values: Any) -> Optional[float]:
        for value in values:
            if value is None or isinstance(value, bool):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    @classmethod
    def _integer(cls, *values: Any) -> Optional[int]:
        value = cls._number(*values)
        return int(value) if value is not None else None

    @staticmethod
    def _text(*values: Any) -> Optional[str]:
        for value in values:
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @classmethod
    def _ratio(cls, numerator: Any, denominator: Any) -> Optional[float]:
        top = cls._number(numerator)
        bottom = cls._number(denominator)
        if top is None or bottom in {None, 0.0}:
            return None
        return round(top / bottom, 4)

    @classmethod
    def _capacity_indicators(cls, profile: Dict[str, Any], requested_amount: Optional[float]) -> Dict[str, Any]:
        revenue = cls._number(profile.get("annual_revenue"), profile.get("revenue"))
        ebitda = cls._number(profile.get("ebitda"))
        operating_cash_flow = cls._number(profile.get("operating_cash_flow"), profile.get("net_operating_cash_flow"))
        annual_debt_service = cls._number(
            profile.get("existing_debt_service"), profile.get("annual_debt_service"), profile.get("debt_service")
        )
        total_debt = cls._number(profile.get("total_debt"), profile.get("existing_debt"))
        equity = cls._number(profile.get("equity"), profile.get("owner_equity"))
        dso = cls._number(profile.get("days_sales_outstanding"), profile.get("dso_days"))
        dio = cls._number(profile.get("inventory_days"), profile.get("dio_days"))
        dpo = cls._number(profile.get("payable_days"), profile.get("dpo_days"))
        return {
            "revenue_available": revenue is not None,
            "cash_flow_capacity_assessable": (ebitda is not None or operating_cash_flow is not None)
            and annual_debt_service is not None,
            "requested_amount_to_annual_revenue": cls._ratio(requested_amount, revenue),
            "ebitda_margin": cls._ratio(ebitda, revenue),
            "debt_to_ebitda": cls._ratio(total_debt, ebitda),
            "debt_to_equity": cls._ratio(total_debt, equity),
            "debt_service_coverage": cls._ratio(
                operating_cash_flow if operating_cash_flow is not None else ebitda,
                annual_debt_service,
            ),
            "working_capital_cycle_days": round(dso + dio - dpo, 2)
            if None not in (dso, dio, dpo)
            else None,
            "collateral_coverage": cls._ratio(profile.get("collateral_value"), requested_amount),
            "calculation_note": "Các tỷ số là chỉ báo mô tả từ dữ liệu đã có, không phải ngưỡng phê duyệt.",
        }

    @staticmethod
    def _repayment_sources(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        explicit = profile.get("repayment_source") or profile.get("primary_repayment_source")
        if explicit:
            sources.append({"type": "primary", "value": explicit, "basis": "confirmed_customer_profile"})
        if profile.get("operating_cash_flow") is not None or profile.get("ebitda") is not None:
            sources.append(
                {
                    "type": "operating_cash_flow",
                    "value": "Dòng tiền từ hoạt động kinh doanh",
                    "basis": "financial_profile",
                }
            )
        if profile.get("collateral_type") or profile.get("collateral_value"):
            sources.append(
                {
                    "type": "secondary_support",
                    "value": profile.get("collateral_type") or "Tài sản bảo đảm chưa phân loại",
                    "basis": "financing_profile",
                }
            )
        return sources

    @staticmethod
    def _analysis_dimensions(
        *,
        profile: Dict[str, Any],
        documents: Dict[str, str],
        indicators: Dict[str, Any],
        hard_blocks: List[Dict[str, Any]],
        missing: List[str],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "dimension": "business_context",
                "facts": {key: profile.get(key) for key in ("industry", "operating_years", "annual_revenue")},
                "assessment": "available" if profile.get("industry") and profile.get("operating_years") else "incomplete",
            },
            {
                "dimension": "borrowing_need",
                "facts": {key: profile.get(key) for key in ("requested_amount_vnd", "amount_vnd", "tenor_months", "purpose")},
                "assessment": "requires_purpose_and_amount_confirmation"
                if not any(profile.get(key) for key in ("requested_amount_vnd", "amount_vnd"))
                else "captured",
            },
            {
                "dimension": "repayment_capacity",
                "facts": indicators,
                "assessment": "assessable" if indicators["cash_flow_capacity_assessable"] else "insufficient_financial_data",
            },
            {
                "dimension": "credit_history_and_compliance",
                "facts": {"has_bad_debt_12m": profile.get("has_bad_debt_12m"), "ubo_status": profile.get("ubo_status")},
                "assessment": "hard_block_detected" if hard_blocks else "no_hard_block_in_current_rule_output",
            },
            {
                "dimension": "collateral",
                "facts": {key: profile.get(key) for key in ("collateral_type", "collateral_value", "collateral_legal_status")},
                "assessment": "captured" if profile.get("collateral_type") or profile.get("collateral_value") else "not_provided",
            },
            {
                "dimension": "document_readiness",
                "facts": documents,
                "assessment": "incomplete" if missing else "initially_complete",
            },
        ]

    @staticmethod
    def _confidence(dimensions: List[Dict[str, Any]]) -> Dict[str, Any]:
        complete = sum(
            item["assessment"]
            in {"available", "captured", "assessable", "initially_complete", "no_hard_block_in_current_rule_output"}
            for item in dimensions
        )
        score = round(complete / max(1, len(dimensions)), 4)
        return {
            "input_completeness": score,
            "level": "high" if score >= 0.8 else "medium" if score >= 0.5 else "low",
            "policy": "credit-analysis-completeness-v1",
        }

    @staticmethod
    def _structure_scenarios(
        *,
        requested_amount: Optional[float],
        requested_tenor_months: Optional[int],
        loan_purpose: Optional[str],
        repayment_sources: List[Dict[str, Any]],
        hard_blocks: List[Dict[str, Any]],
        capacity_assessable: bool,
    ) -> List[Dict[str, Any]]:
        if hard_blocks:
            return [
                {
                    "scenario": "credit_not_structurable_under_current_facts",
                    "status": "blocked",
                    "reason": "Rule Engine đang có hard block; không đề xuất hạn mức/lãi suất thay thế.",
                }
            ]
        return [
            {
                "scenario": "requested_structure",
                "status": "ready_for_credit_officer_review" if capacity_assessable else "needs_financial_analysis",
                "requested_amount": requested_amount,
                "requested_tenor_months": requested_tenor_months,
                "loan_purpose": loan_purpose,
                "repayment_sources": repayment_sources,
                "approved_limit": None,
                "pricing": None,
                "note": "Scenario giữ đúng nhu cầu RM/khách hàng; không phải đề xuất phê duyệt.",
            }
        ]
