import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_DIR = os.getenv("TELEMETRY_DIR", os.path.join("data", "metrics"))


@dataclass
class TelemetryEvent:
    ts: str
    type: str  # counter | histogram | event
    name: str
    value: Optional[float] = None
    labels: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ts": self.ts,
            "type": self.type,
            "name": self.name,
        }
        if self.value is not None:
            d["value"] = self.value
        if self.labels:
            d["labels"] = self.labels
        return d


class TelemetryService:
    """Lightweight JSONL telemetry sink for counters and histograms.

    Design goals:
    - Zero external deps
    - Append-only JSONL for easy ingestion
    - Safe to call from hot paths (best-effort, failures are non-fatal)
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir or DEFAULT_DIR)
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # As fallback, use system temp-like dir under project
            self.base_dir = Path("data") / "metrics"
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def _file_for_today(self) -> Path:
        today = datetime.now(UTC).strftime("%Y%m%d")
        return self.base_dir / f"metrics-{today}.jsonl"

    def _write_jsonl(self, payload: Dict[str, Any]) -> None:
        try:
            fpath = self._file_for_today()
            with fpath.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Non-fatal: swallow telemetry write errors
            pass

    def inc_counter(self, name: str, labels: Optional[Dict[str, Any]] = None) -> None:
        evt = TelemetryEvent(ts=datetime.now(UTC).isoformat(), type="counter", name=name, labels=labels or {})
        self._write_jsonl(evt.to_dict())

    def observe_hist(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None) -> None:
        evt = TelemetryEvent(
            ts=datetime.now(UTC).isoformat(), type="histogram", name=name, value=float(value), labels=labels or {}
        )
        self._write_jsonl(evt.to_dict())

    def log_event(self, name: str, labels: Optional[Dict[str, Any]] = None) -> None:
        evt = TelemetryEvent(ts=datetime.now(UTC).isoformat(), type="event", name=name, labels=labels or {})
        self._write_jsonl(evt.to_dict())

    @contextmanager
    def timeit(self, name: str, labels: Optional[Dict[str, Any]] = None):
        start = time.perf_counter()
        try:
            yield
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            self.observe_hist(name, dur_ms, labels)

    def flush(self) -> None:
        # Append-on-call model; nothing buffered.
        return
