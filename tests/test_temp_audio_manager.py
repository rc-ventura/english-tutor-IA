import os
import time
from pathlib import Path

import pytest

from src.infra.temp_audio_manager import (
    cleanup_older_than,
    enforce_limits,
    maintain_tmp_audio_dir,
)


AUDIO_SUFFIXES = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"]


def _mk_audio_file(dirpath: Path, name: str, size_bytes: int = 0, suffix: str = ".wav") -> Path:
    p = dirpath / f"{name}{suffix}"
    with p.open("wb") as f:
        if size_bytes > 0:
            f.write(b"0" * size_bytes)
        else:
            f.write(b"\x00")
    return p


def test_cleanup_older_than_deletes_old_files(tmp_path: Path):
    base = tmp_path
    # Create old and recent audio files, plus a non-audio file
    old_f = _mk_audio_file(base, "old", suffix=".wav")
    recent_f = _mk_audio_file(base, "recent", suffix=".mp3")
    txt_f = base / "keep.txt"
    txt_f.write_text("hello")

    # Make 'old_f' older than 2 hours
    two_hours_ago = time.time() - 2 * 3600
    os.utime(old_f, (two_hours_ago, two_hours_ago))

    deleted, bytes_deleted = cleanup_older_than(str(base), max_age_hours=1.0)

    assert deleted >= 1
    assert old_f.exists() is False
    # Recent audio and non-audio must remain
    assert recent_f.exists() is True
    assert txt_f.exists() is True


def test_enforce_limits_by_count_deletes_oldest(tmp_path: Path):
    base = tmp_path
    # Create 4 audio files with different mtimes (oldest first)
    f1 = _mk_audio_file(base, "a", suffix=".wav")
    time.sleep(0.01)
    f2 = _mk_audio_file(base, "b", suffix=".mp3")
    time.sleep(0.01)
    f3 = _mk_audio_file(base, "c", suffix=".m4a")
    time.sleep(0.01)
    f4 = _mk_audio_file(base, "d", suffix=".ogg")

    # Enforce at most 2 files
    deleted, bytes_deleted = enforce_limits(str(base), max_total_mb=None, max_files=2)

    assert deleted == 2
    # Oldest two should be gone: f1, f2
    assert f1.exists() is False
    assert f2.exists() is False
    assert f3.exists() is True
    assert f4.exists() is True


def test_enforce_limits_by_size_deletes_until_under_limit(tmp_path: Path):
    base = tmp_path
    # Create 3 audio files of ~1KB each
    f1 = _mk_audio_file(base, "s1", size_bytes=1024)
    f2 = _mk_audio_file(base, "s2", size_bytes=1024)
    f3 = _mk_audio_file(base, "s3", size_bytes=1024)

    # Limit total to ~2KB
    deleted, bytes_deleted = enforce_limits(str(base), max_total_mb=0.002, max_files=None)

    # At least 1 file must be deleted to go under 2KB
    assert deleted >= 1
    remaining = [p for p in base.iterdir() if p.suffix in AUDIO_SUFFIXES]
    # Remaining total should be <= 2KB
    total = sum(p.stat().st_size for p in remaining)
    assert total <= 2048


def test_maintain_tmp_audio_dir_reads_env_and_applies(monkeypatch, tmp_path: Path):
    base = tmp_path

    # Point AUDIO_TMP_DIR to our tmp
    monkeypatch.setenv("AUDIO_TMP_DIR", str(base))
    # Delete files older than 1 hour
    monkeypatch.setenv("AUDIO_TMP_MAX_AGE_HOURS", "1")
    # Keep at most 2 files and <= 1KB total
    monkeypatch.setenv("AUDIO_TMP_MAX_FILES", "2")
    monkeypatch.setenv("AUDIO_TMP_MAX_TOTAL_MB", "0.001")

    # Create 3 audio files; mark one as old
    old_f = _mk_audio_file(base, "old_env", size_bytes=1024)
    mid_f = _mk_audio_file(base, "mid_env", size_bytes=512)
    new_f = _mk_audio_file(base, "new_env", size_bytes=512)

    three_hours_ago = time.time() - 3 * 3600
    os.utime(old_f, (three_hours_ago, three_hours_ago))

    # Also create a non-audio file which should not be touched
    txt_f = base / "note.txt"
    txt_f.write_text("keep me")

    deleted, bytes_deleted = maintain_tmp_audio_dir()

    # Should delete at least the old one, and possibly more to satisfy size/count
    assert deleted >= 1
    assert txt_f.exists() is True

    # Post-conditions: count and size constraints are respected for audio files
    remaining_audio = sorted(
        [p for p in base.iterdir() if p.is_file() and p.suffix in AUDIO_SUFFIXES], key=lambda p: p.stat().st_mtime
    )
    assert len(remaining_audio) <= 2
    total = sum(p.stat().st_size for p in remaining_audio)
    assert total <= 1024
