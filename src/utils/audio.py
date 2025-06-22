import base64
import logging
import tempfile
from typing import Any, Dict, List

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
        _logger.info(f"Audio content saved to temporary file: {tmp_path}")
        return tmp_path
    except Exception as e:
        _logger.error(f"Failed to save audio to temporary file: {e}", exc_info=True)
        raise


def extract_text_from_response(response: Any) -> str:
    """Extrai texto da resposta OpenAI, garantindo que sempre retorne uma string."""
    if not hasattr(response, "choices") or not response.choices:
        return ""

    message = response.choices[0].message
    content = getattr(message, "content", None)
    if content is None or not isinstance(content, (str, list)) and hasattr(message, "text"):
        content = message.text

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
        _logger.info(f"Transcript extracted from message.audio.transcript: {transcript!r}")
        return transcript

    if hasattr(content, "transcript"):
        transcript = getattr(content, "transcript", "")
        _logger.info(f"Transcript extracted from message.content.transcript: {transcript!r}")
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


def encode_file_to_base64(filepath: str) -> str:
    """Encodes a file to a base64 string."""
    try:
        with open(filepath, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")
    except Exception as e:
        _logger.error(f"Error encoding file {filepath} to base64: {e}", exc_info=True)
        raise
