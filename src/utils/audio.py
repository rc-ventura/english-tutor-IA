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
    """Extrai o áudio em base64 da resposta da OpenAI."""
    if not hasattr(response, "choices") or not response.choices:
        return None

    message = response.choices[0].message
    if hasattr(message, "audio") and hasattr(message.audio, "data") and message.audio.data:
        return message.audio.data

    _logger.warning("No audio data found in the response.")
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
