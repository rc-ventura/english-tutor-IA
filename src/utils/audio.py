import base64
import logging
import tempfile
from typing import Any, Dict, List

from pydub import AudioSegment

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
