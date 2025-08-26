import json
import os
import shutil
import tempfile
from pathlib import Path

from src.infra.telemetry import TelemetryService


def read_jsonl(path: Path):
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def test_telemetry_writes_jsonl():
    tmpdir = tempfile.mkdtemp(prefix="telemetry_test_")
    try:
        t = TelemetryService(base_dir=tmpdir)

        # Emit some metrics
        t.inc_counter("audio_attempts_total", {"model": "demo", "voice": "alloy"})
        t.observe_hist("multimodal_latency_ms", 123.4, {"model": "demo"})
        with t.timeit("block_latency_ms", {"unit": "test"}):
            pass

        # Locate today's file
        files = list(Path(tmpdir).glob("metrics-*.jsonl"))
        assert files, "No telemetry file created"
        content = read_jsonl(files[0])

        # There should be at least 3 records
        assert len(content) >= 3

        names = [c.get("name") for c in content]
        assert "audio_attempts_total" in names
        assert "multimodal_latency_ms" in names
        assert "block_latency_ms" in names

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
