import os
import time
import logging
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"}


def _list_audio_files(tmp_dir: Path) -> List[Path]:
    if not tmp_dir.exists():
        return []
    files: List[Path] = []
    for p in tmp_dir.iterdir():
        if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES:
            files.append(p)
    return files


def _total_size(files: Iterable[Path]) -> int:
    total = 0
    for f in files:
        try:
            total += f.stat().st_size
        except Exception:
            pass
    return total


def _delete_files(files: Iterable[Path]) -> Tuple[int, int]:
    deleted = 0
    bytes_deleted = 0
    for f in files:
        try:
            sz = 0
            try:
                sz = f.stat().st_size
            except Exception:
                sz = 0
            f.unlink(missing_ok=True)
            deleted += 1
            bytes_deleted += sz
        except Exception as e:
            _logger.debug("Failed to delete %s: %s", f, e)
    return deleted, bytes_deleted


def cleanup_older_than(base_dir: str, max_age_hours: float) -> Tuple[int, int]:
    """Delete files older than max_age_hours. Returns (files_deleted, bytes_deleted)."""
    tmp_dir = Path(base_dir)
    files = _list_audio_files(tmp_dir)
    if not files:
        return (0, 0)
    cutoff = time.time() - max(0.0, float(max_age_hours)) * 3600.0
    old_files = [f for f in files if f.stat().st_mtime < cutoff]
    if not old_files:
        return (0, 0)
    old_files.sort(key=lambda p: p.stat().st_mtime)
    deleted, bytes_deleted = _delete_files(old_files)
    if deleted:
        _logger.info("TempAudioManager: deleted %d old files (%.1f KB)", deleted, bytes_deleted / 1024.0)
    return deleted, bytes_deleted


def enforce_limits(
    base_dir: str, max_total_mb: Optional[float] = None, max_files: Optional[int] = None
) -> Tuple[int, int]:
    """Ensure directory stays under size and file-count limits by deleting oldest files.
    Returns (files_deleted, bytes_deleted)."""
    tmp_dir = Path(base_dir)
    files = _list_audio_files(tmp_dir)
    if not files:
        return (0, 0)

    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)  # oldest first

    deleted = 0
    bytes_deleted = 0

    # Enforce file count first
    if isinstance(max_files, int) and max_files > 0 and len(files_sorted) > max_files:
        over = len(files_sorted) - max_files
        to_delete = files_sorted[:over]
        d, b = _delete_files(to_delete)
        deleted += d
        bytes_deleted += b
        files_sorted = files_sorted[over:]

    # Enforce total size
    if isinstance(max_total_mb, (int, float)) and max_total_mb > 0:
        limit_bytes = int(max_total_mb * 1024 * 1024)
        current_bytes = _total_size(files_sorted)
        idx = 0
        while current_bytes > limit_bytes and idx < len(files_sorted):
            f = files_sorted[idx]
            idx += 1
            try:
                sz = f.stat().st_size
            except Exception:
                sz = 0
            try:
                f.unlink(missing_ok=True)
                deleted += 1
                bytes_deleted += sz
                current_bytes -= sz
            except Exception as e:
                _logger.debug("Failed to delete for size limit %s: %s", f, e)

    if deleted:
        _logger.info("TempAudioManager: deleted %d files to enforce limits (%.1f KB)", deleted, bytes_deleted / 1024.0)
    return deleted, bytes_deleted


def maintain_tmp_audio_dir(
    base_dir: Optional[str] = None,
    max_age_hours: Optional[float] = None,
    max_total_mb: Optional[float] = None,
    max_files: Optional[int] = None,
) -> Tuple[int, int]:
    """Convenience wrapper that reads env defaults when args are None and applies cleanup and limits."""
    base_dir = base_dir or os.getenv("AUDIO_TMP_DIR", os.path.join("data", "audio", "tmp"))
    max_age_env = os.getenv("AUDIO_TMP_MAX_AGE_HOURS")
    max_total_env = os.getenv("AUDIO_TMP_MAX_TOTAL_MB")
    max_files_env = os.getenv("AUDIO_TMP_MAX_FILES")

    if max_age_hours is None and max_age_env:
        try:
            max_age_hours = float(max_age_env)
        except Exception:
            max_age_hours = None
    if max_total_mb is None and max_total_env:
        try:
            max_total_mb = float(max_total_env)
        except Exception:
            max_total_mb = None
    if max_files is None and max_files_env:
        try:
            max_files = int(max_files_env)
        except Exception:
            max_files = None

    total_deleted = 0
    total_bytes = 0

    if max_age_hours and max_age_hours > 0:
        d, b = cleanup_older_than(base_dir, max_age_hours)
        total_deleted += d
        total_bytes += b

    if (max_total_mb and max_total_mb > 0) or (max_files and max_files > 0):
        d, b = enforce_limits(base_dir, max_total_mb=max_total_mb, max_files=max_files)
        total_deleted += d
        total_bytes += b

    return total_deleted, total_bytes
