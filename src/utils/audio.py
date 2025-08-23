import base64
import logging
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import os
import re

from pydub import AudioSegment
from pydub.silence import detect_nonsilent

# Configure o logger para este módulo
_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def save_audio_to_temp_file(audio_bytes: bytes, suffix: str = ".wav") -> str:
    """Saves audio bytes to a temporary file and returns the file path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        return tmp_path
    except Exception as e:
        _logger.error(f"Failed to save audio to temporary file: {e}", exc_info=True)
        raise


def extract_text_from_response(response: Any) -> str:
    """Extrai texto da resposta OpenAI, garantindo que sempre retorne uma string."""
    if not hasattr(response, "choices") or not response.choices:
        return ""

    message = response.choices[0].message
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # Search for the first text block in the content list
        for item in content:
            if isinstance(item, Dict) and item.get("type") == "text":
                return item.get("text", "")

    # Fallback for older or different response structures
    if content is None and hasattr(message, "audio") and hasattr(message.audio, "transcript"):
        transcript = getattr(message.audio, "transcript", "")
        return transcript

    if hasattr(content, "transcript"):
        transcript = getattr(content, "transcript", "")
        return transcript

    _logger.warning(f"Could not extract text from response. Content type: {type(content)}")
    return ""


def extract_audio_from_response(response: Any) -> str | None:
    """Extrai o áudio em base64 da resposta da OpenAI.
    Suporta estruturas antigas (message.audio.data) e novas (content parts com type=output_audio/audio).
    """
    if not hasattr(response, "choices") or not response.choices:
        return None

    message = response.choices[0].message

    # 1) Forma antiga: message.audio.data
    try:
        if hasattr(message, "audio") and message.audio is not None:
            data = getattr(message.audio, "data", None)
            if data:
                return data
    except Exception:
        pass

    # 2) Forma nova: content como lista de partes (ex.: type="output_audio" ou "audio")
    try:
        content = getattr(message, "content", None)
        # content pode ser string (texto puro) ou lista de partes
        if isinstance(content, list):
            for part in content:
                # Suporta acesso tanto por atributo quanto por dict
                p_type = getattr(part, "type", None) or (isinstance(part, dict) and part.get("type"))
                if p_type in ("output_audio", "audio"):
                    audio_obj = getattr(part, "audio", None) or (isinstance(part, dict) and part.get("audio"))
                    if audio_obj:
                        # Tente extrair o base64 (data)
                        data = getattr(audio_obj, "data", None) or (
                            isinstance(audio_obj, dict) and audio_obj.get("data")
                        )
                        if data:
                            return data
                        # Alguns formatos podem expor "id"/"url" ao invés de data; log para diagnóstico
                        url = getattr(audio_obj, "url", None) or (isinstance(audio_obj, dict) and audio_obj.get("url"))
                        if url:
                            _logger.info("Audio part has URL instead of inline data (url=%s)", url)
    except Exception as e:
        _logger.debug("Failed to parse content parts for audio: %s", e)

    # 3) Sem áudio encontrado: diagnóstico detalhado
    _logger.warning("No audio data found in the response.")
    try:
        resp_type = type(response).__name__
        # Captura tipos das partes de conteúdo, se existirem
        content_types = None
        try:
            c = getattr(response.choices[0].message, "content", None)
            if isinstance(c, list):

                def part_desc(p: Any) -> str:
                    t = getattr(p, "type", None) or (isinstance(p, dict) and p.get("type"))
                    has_audio = hasattr(p, "audio") or (isinstance(p, dict) and ("audio" in p))
                    return f"type={t},has_audio={has_audio}"

                content_types = [part_desc(p) for p in c]
        except Exception:
            content_types = None

        has_msg_audio_attr = hasattr(message, "audio") and getattr(message, "audio") is not None
        _logger.info(
            "Audio missing - response shape: type=%s has_msg_audio_attr=%s content_parts=%s",
            resp_type,
            has_msg_audio_attr,
            content_types,
        )
    except Exception as e:
        _logger.info("Audio missing - failed to inspect response shape: %s", e)
    return None


def get_audio_duration(file_path: str) -> float:
    """Calculates the duration of an audio file in seconds."""
    if not file_path:
        return 0.0
    try:
        audio = AudioSegment.from_file(file_path)
        duration_seconds = len(audio) / 1000.0
        return duration_seconds
    except Exception as e:
        _logger.error(f"Failed to get duration for audio file {file_path}: {e}", exc_info=True)
        return 0.0  # Return 0 if duration can't be determined


# ---------------- Pronunciation Metrics ----------------
def _level_wpm_range(level: Optional[str]) -> Tuple[int, int]:
    level = (level or "B1").upper()
    ranges = {
        "A1": (80, 140),
        "A2": (100, 160),
        "B1": (110, 180),
        "B2": (120, 200),
        "C1": (130, 210),
        "C2": (140, 220),
    }
    return ranges.get(level, (110, 180))


def _safe_dbfs(val: float) -> float:
    # pydub uses -inf for silence; clamp to a reasonable floor
    if val == float("-inf"):
        return -90.0
    return float(val)


def analyze_pronunciation_metrics(
    file_path: str,
    transcript: Optional[str] = None,
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute lightweight pronunciation metrics using pydub.

    Returns keys:
    - duration_sec, speaking_time_sec, speech_ratio, pause_ratio
    - rms_dbfs, peak_dbfs, clipping_ratio
    - words, wps, wpm (if transcript provided)
    - suggested_escalation (bool), reasons (list)
    - pronunciation_score (0-100), pronunciation_reasons (list[str])
    - word_scores (optional, None for MVP)
    """
    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        _logger.error("Failed to load audio for metrics: %s", e, exc_info=True)
        raise

    duration_ms = max(0, len(audio))
    duration_sec = duration_ms / 1000.0 if duration_ms else 0.0

    # Non-silent detection
    dbfs = _safe_dbfs(audio.dBFS)
    silence_thresh = dbfs - 16.0
    try:
        nonsilent = detect_nonsilent(audio, min_silence_len=200, silence_thresh=silence_thresh)
    except Exception:
        nonsilent = []
    speaking_ms = sum(max(0, end - start) for start, end in nonsilent)
    speaking_time_sec = speaking_ms / 1000.0
    speech_ratio = (speaking_ms / duration_ms) if duration_ms else 0.0
    pause_ratio = max(0.0, 1.0 - speech_ratio)

    # Loudness & clipping
    rms_dbfs = _safe_dbfs(audio.dBFS)
    peak_dbfs = _safe_dbfs(audio.max_dBFS)
    samples = audio.get_array_of_samples()
    total_samples = max(1, len(samples))
    # Max possible amplitude for sample width
    max_possible = float(2 ** (8 * audio.sample_width - 1) - 1)
    threshold = 0.98 * max_possible
    clipped = 0
    try:
        for s in samples:
            if abs(int(s)) >= threshold:
                clipped += 1
    except Exception:
        clipped = 0
    clipping_ratio = clipped / total_samples

    # Words per second/minute from transcript (optional)
    words = None
    wps = None
    wpm = None
    if transcript:
        # Rough tokenization into words (supports simple unicode letters/numbers)
        tokens = re.findall(r"[\w\dÀ-ÖØ-öø-ÿ']+", transcript, flags=re.UNICODE)
        words = len(tokens)
        if speaking_time_sec > 0:
            wps = words / speaking_time_sec
            wpm = wps * 60.0

    # Simple rule-based suggestion (technical, for escalation)
    reasons: List[str] = []
    if duration_sec < 1.0:
        reasons.append("too_short")
    if pause_ratio > 0.6:
        reasons.append("high_pause_ratio")
    if clipping_ratio > 0.02:
        reasons.append("clipping_detected")
    if wpm is not None:
        wmin, wmax = _level_wpm_range(level)
        tolerance = 15
        if wpm < (wmin - tolerance):
            reasons.append("too_slow_for_level")
        if wpm > (wmax + tolerance):
            reasons.append("too_fast_for_level")

    suggested = len(reasons) > 0

    # ---------------- Pronunciation proxy (MVP) ----------------
    # Start from 100 and apply penalties based on clarity proxies.
    pron_reasons: List[str] = []
    score = 100.0

    # Duration very short -> large penalty
    if duration_sec < 1.0:
        score -= 30
        pron_reasons.append("too_short")

    # Pause ratio: >0.6 strong penalty, else mild proportional penalty
    if pause_ratio > 0.6:
        score -= 25
        pron_reasons.append("high_pause_ratio")
    else:
        score -= max(0.0, (pause_ratio - 0.3) / 0.3) * 15.0  # 0..15 penalty between 30%-60%
        if pause_ratio > 0.3:
            pron_reasons.append("moderate_pauses")

    # Clipping
    if clipping_ratio > 0.02:
        score -= 25
        pron_reasons.append("clipping_detected")
    elif clipping_ratio > 0.005:
        score -= 10
        pron_reasons.append("slight_clipping")

    # Loudness window: target around -20..-12 dBFS
    if rms_dbfs <= -40:
        score -= 30
        pron_reasons.append("very_low_volume")
    elif rms_dbfs <= -28:
        score -= 15
        pron_reasons.append("low_volume")
    elif rms_dbfs >= -6:
        score -= 25
        pron_reasons.append("too_loud")
    elif rms_dbfs >= -10:
        score -= 10
        pron_reasons.append("loud")

    # Very low speech content overall
    if speech_ratio < 0.3:
        score -= 15
        pron_reasons.append("low_speech_ratio")

    # Clamp score
    pronunciation_score = int(max(0, min(100, round(score))))

    # MVP: word-level scores not yet computed
    word_scores = None

    return {
        "duration_sec": duration_sec,
        "speaking_time_sec": speaking_time_sec,
        "speech_ratio": speech_ratio,
        "pause_ratio": pause_ratio,
        "rms_dbfs": rms_dbfs,
        "peak_dbfs": peak_dbfs,
        "clipping_ratio": clipping_ratio,
        "words": words,
        "wps": wps,
        "wpm": wpm,
        "level": level,
        "suggested_escalation": suggested,
        "reasons": reasons,
        "pronunciation_score": pronunciation_score,
        "pronunciation_reasons": pron_reasons,
        "word_scores": word_scores,
    }
