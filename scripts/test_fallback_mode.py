"""Test invalid API key fallback degradation behavior."""

from __future__ import annotations

import asyncio
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.agents.base import BaseExpertRuntime


async def main():
    print("Testing BaseExpertRuntime fallback with invalid API key...")
    # Temporarily override settings
    import app.config as app_config
    app_config.settings.AGENTIC_LLM_ENABLED = True
    app_config.settings.DEFAULT_LLM = "google"
    app_config.settings.GOOGLE_API_KEY = "invalid-demo-key"
    app_config.settings.MODEL_TIMEOUT_SECONDS = 3.0

    runtime = BaseExpertRuntime()
    result = await runtime._enrich(
        system_prompt="Test system prompt",
        payload={"test": "payload"}
    )
    print("Result status:", result.get("status"))
    print("Decision rationale summary:", result.get("decision_rationale_summary"))
    print("Last fallback reason:", runtime.last_fallback_reason)

    assert result.get("status") in {"NEED_REVIEW", "CONDITIONAL"}, "Status must be safe"
    assert runtime.last_fallback_reason is not None, "Fallback reason must be recorded"
    print("\n✅ INVALID KEY FALLBACK TEST PASSED (NO CRASH)")


if __name__ == "__main__":
    asyncio.run(main())
