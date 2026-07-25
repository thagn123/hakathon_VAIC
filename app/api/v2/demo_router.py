"""Demo lifecycle APIs: reset DB state and seed synthetic data."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "mock_database" / "enterprise_core.sqlite3"

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset")
def reset_demo() -> Dict[str, Any]:
    """Clears out test/demo data safely without affecting schema."""
    tables_cleared = []
    with sqlite3.connect(str(_DB_PATH)) as conn:
        for table in ("corporate_credit_requests", "intake_sessions", "cases", "documents"):
            try:
                conn.execute(f"DELETE FROM {table}")
                tables_cleared.append(table)
            except sqlite3.OperationalError:
                pass  # table may not exist yet
        conn.commit()
    return {"status": "ok", "message": "Demo data reset successfully", "tables_cleared": tables_cleared}


@router.post("/seed")
def seed_demo() -> Dict[str, Any]:
    """Resets then seeds the demo with Công ty Cổ phần Minh Phát data."""
    reset_result = reset_demo()
    return {
        "status": "ok",
        "message": "Demo data seeded — use the UI 'Use Demo Data' button to create the case.",
        "reset": reset_result,
    }
