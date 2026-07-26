"""Dependency-free observability suitable for the local MVP."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict


class Metrics:
    def __init__(self) -> None:
        self._values: Counter[str] = Counter()
        self._lock = RLock()

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._values[name] += value

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._values)


metrics = Metrics()


class JsonEventLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()
    def emit(self, event_code: str, **fields: Any) -> None:
        forbidden = {"token", "approval_token", "secret", "password", "email_body", "identity_number"}
        record = {
            "at": datetime.now(timezone.utc).isoformat(),
            "event_code": event_code,
            **{key: "[REDACTED]" if key.lower() in forbidden else value for key, value in fields.items()},
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock, self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            logging.getLogger("app.events").warning(f"Failed to write event log to disk: {exc}")
        logging.getLogger("app.events").info(event_code, extra={"event": record})
