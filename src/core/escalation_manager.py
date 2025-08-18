from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote


@dataclass
class EscalationRecord:
    id: str
    created_at: str
    status: str  # "queued" | "resolved"
    source: Optional[str] = None  # "speaking" | "writing"
    practice_mode: Optional[str] = None  # "Hybrid" | "Immersive" | None
    level: Optional[str] = None  # A1..C2
    message_index: Optional[int] = None
    reasons: Optional[List[str]] = None
    user_note: Optional[str] = None
    assistant_text: Optional[str] = None
    user_last_text: Optional[str] = None
    history_preview: Optional[List[Dict[str, Any]]] = None
    audio_relpath: Optional[str] = None
    audio_url_at_submit: Optional[str] = None
    user_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    resolved_at: Optional[str] = None
    resolution_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "status": self.status,
            "source": self.source,
            "practice_mode": self.practice_mode,
            "level": self.level,
            "message_index": self.message_index,
            "reasons": self.reasons,
            "user_note": self.user_note,
            "assistant_text": self.assistant_text,
            "user_last_text": self.user_last_text,
            "history_preview": self.history_preview,
            "audio_relpath": self.audio_relpath,
            "audio_url_at_submit": self.audio_url_at_submit,
            "user_id": self.user_id,
            "meta": self.meta,
            "resolved_at": self.resolved_at,
            "resolution_note": self.resolution_note,
        }


class EscalationManager:
    """Manages creation, listing, and resolution of human escalations using JSONL storage."""

    def __init__(self, base_dir: Optional[Path | str] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path("user_data")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.base_dir / "escalations.jsonl"
        self.audio_dir = self.base_dir / "audio" / "escalations"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    # --------------- Public API ---------------
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new escalation record from a raw payload dict and persist it.

        Returns the full record as dict.
        """
        now = datetime.now(timezone.utc).isoformat()
        esc_id = str(uuid.uuid4())

        # Normalize history preview: keep last N=8 and truncate content strings
        history_preview = payload.get("historyPreview") or []
        if isinstance(history_preview, list):
            history_preview = self._trim_history_preview(history_preview, max_messages=8, max_chars=500)

        audio_url = payload.get("audioUrl")
        audio_relpath = None
        try:
            audio_relpath = self._maybe_persist_audio(audio_url, esc_id) if audio_url else None
        except Exception:
            # Audio copy failure should not block escalation creation
            audio_relpath = None

        record = EscalationRecord(
            id=esc_id,
            created_at=now,
            status="queued",
            source=payload.get("source"),
            practice_mode=payload.get("practiceMode"),
            level=payload.get("level"),
            message_index=payload.get("messageIndex"),
            reasons=payload.get("reasons"),
            user_note=payload.get("userNote"),
            assistant_text=payload.get("assistantText"),
            user_last_text=payload.get("userLastText"),
            history_preview=history_preview,
            audio_relpath=audio_relpath,
            audio_url_at_submit=audio_url,
            user_id=payload.get("userId"),
            meta=payload.get("meta"),
        )

        self._append_jsonl(record.to_dict())
        return record.to_dict()

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List escalation records, optionally filtered by status."""
        if not self.store_path.exists():
            return []
        records = []
        with self.store_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if status is None or rec.get("status") == status:
                        records.append(rec)
                except json.JSONDecodeError:
                    continue
        return records

    def resolve(self, escalation_id: str, note: Optional[str] = None) -> Dict[str, Any]:
        """Mark an escalation as resolved and persist the update via rewrite."""
        records = self.list()  # read all
        found = None
        for rec in records:
            if rec.get("id") == escalation_id:
                rec["status"] = "resolved"
                rec["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if note:
                    rec["resolution_note"] = note
                found = rec
                break
        if not found:
            raise ValueError(f"Escalation id not found: {escalation_id}")
        # Rewrite file atomically
        tmp = self.store_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp.replace(self.store_path)
        return found

    def get(self, escalation_id: str) -> Optional[Dict[str, Any]]:
        """Return a single escalation by id, or None if not found."""
        for rec in self.list():
            if rec.get("id") == escalation_id:
                return rec
        return None

    # --------------- Internal helpers ---------------
    def _append_jsonl(self, rec: Dict[str, Any]) -> None:
        with self.store_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _trim_history_preview(
        self, history: List[Dict[str, Any]], *, max_messages: int, max_chars: int
    ) -> List[Dict[str, Any]]:
        trimmed = history[-max_messages:]
        out: List[Dict[str, Any]] = []
        for msg in trimmed:
            m = dict(msg)
            content = m.get("content")
            if isinstance(content, str) and len(content) > max_chars:
                m["content"] = content[:max_chars] + "…"
            out.append(m)
        return out

    def _maybe_persist_audio(self, audio_url: str, escalation_id: str) -> Optional[str]:
        """Attempt to copy a local Gradio-served file referenced by `audio_url`.

        Supports URLs like "http://host/file=/abs/path/to/file.wav".
        Returns a relative path under user_data/audio/escalations or None on failure.
        """
        if not audio_url:
            return None
        # Try to parse local path from Gradio URL or accept direct paths
        local_path = self._parse_local_path_from_url(audio_url)
        if not local_path or not os.path.exists(local_path):
            return None

        src = Path(local_path)
        ext = src.suffix or ".wav"
        dest = self.audio_dir / f"{escalation_id}{ext}"
        shutil.copy2(src, dest)
        # return relative path from project root
        return str(dest.as_posix())

    def _parse_local_path_from_url(self, audio_url: str) -> Optional[str]:
        """Extract a local filesystem path from a Gradio-style file URL.

        Examples:
        - http://localhost:7860/file=/Users/me/tmp/bot.wav -> /Users/me/tmp/bot.wav
        - http://localhost:7860/file=%2FUsers%2Fme%2Ftmp%2Fbot.wav -> /Users/me/tmp/bot.wav
        - /Users/me/tmp/bot.wav -> /Users/me/tmp/bot.wav
        """
        if not audio_url:
            return None
        # Direct local path
        if os.path.isabs(audio_url) and os.path.exists(audio_url):
            return audio_url
        # Gradio format contains "file=" parameter
        if "file=" in audio_url:
            local_path = audio_url.split("file=")[-1]
            # Strip query params if present
            if "?" in local_path:
                local_path = local_path.split("?")[0]
            # Percent-decode
            local_path = unquote(local_path)
            return local_path
        return None
