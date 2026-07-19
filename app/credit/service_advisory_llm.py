"""LLM-backed service advisory (agent #2).

The LLM *chooses* which services apply and writes the reasons/summary, but it
may only pick from a fixed catalog (allowlist) so it can never invent a banking
product. If the LLM is disabled, unconfigured or returns an invalid shape, the
caller falls back to the deterministic rule-based advisory.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.agents.base import BaseExpertRuntime


# Catalog the LLM is allowed to select from. Keys are the only valid service
# names; values are the accepted priority ceiling shown to the model.
SERVICE_CATALOG: Dict[str, str] = {
    "Vốn lưu động / hạn mức tín dụng": "high",
    "Gói quản lý dòng tiền / CASA": "high",
    "LC / Bảo lãnh thanh toán quốc tế": "medium",
    "Bảo hiểm tài sản đảm bảo": "medium",
    "Internet Banking doanh nghiệp / chi hộ lương": "low",
}

_ALLOWED_PRIORITIES = {"high", "medium", "low"}

_SYSTEM_PROMPT = (
    "Bạn là chuyên viên tư vấn bán chéo dịch vụ ngân hàng doanh nghiệp của SHB. "
    "Dựa trên hồ sơ tín dụng, hãy chọn các dịch vụ phù hợp CHỈ TỪ danh mục cho phép "
    "và viết lý do ngắn bám sát số liệu thật của khách (CASA, doanh thu, ngành, TSĐB, loại đề nghị). "
    "Không được đề xuất dịch vụ ngoài danh mục. Không quyết định phê duyệt tín dụng. "
    "Trả JSON: {\"services\":[{\"service\":<tên đúng trong danh mục>,\"priority\":\"high|medium|low\","
    "\"reason\":<lý do bám dữ liệu>}], \"summary\":<một câu tóm tắt>}."
)


class ServiceAdvisoryRuntime(BaseExpertRuntime):
    def _validate(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raw_services = parsed.get("services")
        if not isinstance(raw_services, list) or not raw_services:
            return None
        services: List[Dict[str, Any]] = []
        for item in raw_services:
            if not isinstance(item, dict):
                continue
            name = item.get("service")
            if name not in SERVICE_CATALOG:  # allowlist guardrail
                continue
            priority = item.get("priority")
            if priority not in _ALLOWED_PRIORITIES:
                priority = SERVICE_CATALOG[name]
            reason = str(item.get("reason", "")).strip()
            if not reason:
                continue
            services.append({"service": name, "priority": priority, "reason": reason})
        if not services:
            return None
        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            names = ", ".join(s["service"] for s in services[:3])
            summary = f"đề xuất {len(services)} dịch vụ (ưu tiên: {names})."
        return {
            "services": services,
            "summary": f"[AI:Gemini] {summary} Credit Specialist chọn dịch vụ khi phê duyệt cuối.",
            "source": "llm",
        }

    async def _advise(self, facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = {"credit_facts": facts, "allowed_services": list(SERVICE_CATALOG.keys())}
        parsed = await self._enrich(system_prompt=_SYSTEM_PROMPT, payload=payload)
        if parsed is None:
            return None
        return self._validate(parsed)

    def advise(self, facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sync bridge for the sync credit router. Returns ``None`` to fall back."""
        if self.client is None:
            return None
        try:
            return asyncio.run(self._advise(facts))
        except RuntimeError:
            # already inside an event loop: run in a fresh loop on this thread
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._advise(facts))
            finally:
                loop.close()
        except Exception:
            return None
