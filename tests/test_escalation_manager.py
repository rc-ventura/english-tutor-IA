import json
import os
from pathlib import Path

from src.core.escalation_manager import EscalationManager


def test_create_writes_jsonl_and_returns_id(tmp_path: Path):
    base = tmp_path / "user_data"
    mgr = EscalationManager(base_dir=base)

    payload = {
        "source": "speaking",
        "practiceMode": "Hybrid",
        "level": "B1",
        "messageIndex": 3,
        "reasons": ["Pronunciation"],
        "assistantText": "Try saying it like...",
        "userLastText": "I said ...",
        "historyPreview": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
        "userId": "anon-123",
        "meta": {"speech_rate": 140},
    }

    rec = mgr.create(payload)

    assert rec["id"] and isinstance(rec["id"], str)
    assert rec["status"] == "queued"

    jsonl = base / "escalations.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["assistant_text"] == payload["assistantText"]
    assert stored["history_preview"][0]["role"] == "user"


def test_list_filters_by_status(tmp_path: Path):
    base = tmp_path / "user_data"
    mgr = EscalationManager(base_dir=base)

    a = mgr.create({})
    b = mgr.create({})
    mgr.resolve(a["id"])  # mark one as resolved

    all_items = mgr.list()
    queued = mgr.list(status="queued")
    resolved = mgr.list(status="resolved")

    assert len(all_items) == 2
    assert len(queued) == 1
    assert len(resolved) == 1
    assert resolved[0]["id"] == a["id"]


def test_resolve_updates_record(tmp_path: Path):
    base = tmp_path / "user_data"
    mgr = EscalationManager(base_dir=base)

    rec = mgr.create({})
    updated = mgr.resolve(rec["id"], note="done")

    assert updated["status"] == "resolved"
    assert updated["resolution_note"] == "done"
    # Ensure file rewritten with the update
    items = mgr.list(status="resolved")
    assert any(i["id"] == rec["id"] for i in items)


def test_audio_copy_from_gradio_file_url(tmp_path: Path):
    base = tmp_path / "user_data"
    mgr = EscalationManager(base_dir=base)

    # create fake audio file
    audio_src = tmp_path / "bot.wav"
    audio_src.write_bytes(b"RIFF....WAVEfake")

    audio_url = f"http://localhost/file={audio_src.as_posix()}"

    rec = mgr.create({"audioUrl": audio_url})

    assert rec["audio_relpath"], "Should copy audio into user_data/audio/escalations"
    copied = Path(rec["audio_relpath"]).resolve()
    assert copied.exists()
    assert copied.read_bytes() == audio_src.read_bytes()
