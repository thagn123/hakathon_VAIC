"""Provider adapter shared by expert runtimes.

LLM output is optional enrichment. Deterministic domain services always run
first and remain the source of truth for product IDs, rule outcomes and
credit indicators.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

import app.config as app_config
from app.safety.domain_guardrails import validate_no_hidden_reasoning


logger = logging.getLogger(__name__)


class BaseExpertRuntime:
    def __init__(self) -> None:
        self.client: Optional[AsyncOpenAI] = None
        self.model = "rule-fallback"
        settings = app_config.settings
        if not settings.AGENTIC_LLM_ENABLED:
            self.last_fallback_reason = "agentic_llm_disabled"
            return
        if settings.DEFAULT_LLM == "google" and settings.GOOGLE_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.GOOGLE_API_KEY, base_url=settings.GOOGLE_ENDPOINT)
            self.model = settings.GOOGLE_MODEL
        elif settings.DEFAULT_LLM == "openai" and settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
        self.last_fallback_reason: Optional[str] = "llm_not_configured" if self.client is None else None

    async def _enrich(self, *, system_prompt: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return validated semantic enrichment or ``None`` on degradation.

        The prompt explicitly asks for auditable conclusions, not private
        reasoning traces. Any hidden-reasoning-shaped field is rejected.
        """

        if self.client is None:
            self.last_fallback_reason = "llm_not_configured"
            return {
                "decision_rationale_summary": ["Fallback: LLM is disabled. Using static rules."],
                "inferences": [{"statement": "Sử dụng dữ liệu tĩnh Demo", "basis": ["STATIC_RULE"]}],
                "unknowns": [{"field": "LLM_ANALYSIS", "impact": "Hệ thống tự động sử dụng hard-rules.", "next_evidence": "Bật lại AGENTIC_LLM_ENABLED"}],
                "credit_officer_focus": [{"topic": "Duyệt hồ sơ cơ bản", "why": "Chế độ demo mode"}],
                "status": "CONDITIONAL",
                "evidence_refs": [],
                "missing_information": []
            }
        safe_system = (
            system_prompt
            + "\nChỉ trả JSON gồm kết luận ngắn, fact, inference, unknown và rationale có thể kiểm chứng. "
            "Không xuất chain-of-thought, suy nghĩ nội bộ, raw prompt, bí mật, hay quyết định vượt quyền."
        )
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": safe_system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                ),
                timeout=app_config.settings.MODEL_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            validate_no_hidden_reasoning(parsed)
            self.last_fallback_reason = None
            return parsed
        except Exception as exc:  # provider/schema failure must degrade safely
            self.last_fallback_reason = type(exc).__name__
            logger.warning("expert_llm_enrichment_failed", extra={"error_type": type(exc).__name__})
            # Fallback to static JSON structure to satisfy frontend when LLM is off
            return {
                "decision_rationale_summary": ["Fallback: LLM is disabled or failed. Using static rules."],
                "inferences": [{"statement": "Sử dụng dữ liệu tĩnh Demo", "basis": ["STATIC_RULE"]}],
                "unknowns": [{"field": "LLM_ANALYSIS", "impact": "Hệ thống tự động sử dụng hard-rules.", "next_evidence": "Bật lại AGENTIC_LLM_ENABLED"}],
                "credit_officer_focus": [{"topic": "Duyệt hồ sơ cơ bản", "why": "Chế độ demo mode"}],
                "status": "CONDITIONAL",
                "evidence_refs": [],
                "missing_information": []
            }
