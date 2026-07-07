"""
Structured JSON logger for Greenroom backend.

All log output is a single JSON object per line so Azure Log Analytics
(and any other log aggregator) can parse and query it without a custom
parser. Use this module instead of print() or the stdlib logging module.

Usage:
    from services.logger import log
    log.info("piston.run", language="python", latency_ms=123)
    log.error("llm.failed", error=str(exc), track="technical")
    log.warning("guardrail.triggered", track="technical", draft_len=200)
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone


class _Logger:
    def _emit(self, level: str, event: str, **fields) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **fields,
        }
        print(json.dumps(record, default=str), file=sys.stdout, flush=True)

    def info(self, event: str, **fields) -> None:
        self._emit("INFO", event, **fields)

    def warning(self, event: str, **fields) -> None:
        self._emit("WARNING", event, **fields)

    def error(self, event: str, **fields) -> None:
        self._emit("ERROR", event, **fields)

    def debug(self, event: str, **fields) -> None:
        self._emit("DEBUG", event, **fields)

    @contextmanager
    def timed(self, event: str, **fields):
        """Context manager that logs event with latency_ms on exit."""
        start = time.monotonic()
        try:
            yield
        except Exception as exc:
            elapsed = round((time.monotonic() - start) * 1000)
            self._emit("ERROR", event, latency_ms=elapsed, error=str(exc), **fields)
            raise
        else:
            elapsed = round((time.monotonic() - start) * 1000)
            self._emit("INFO", event, latency_ms=elapsed, **fields)


log = _Logger()
