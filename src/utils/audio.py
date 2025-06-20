import base64
import io
import logging
from typing import Union

from pydub import AudioSegment
from pydub.playback import play

# Configure o logger para este módulo
_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def play_audio(audio: Union[str, bytes], format: str = "wav"):
    """Plays audio from a file path or bytes. This is a blocking call."""
    try:
        if isinstance(audio, str):
            _logger.info(f"Playing audio from file: {audio}")
            sound = AudioSegment.from_file(audio)
        else:
            _logger.info("Playing audio from memory")
            audio_file = io.BytesIO(audio)
            sound = AudioSegment.from_file(audio_file, format=format)
        play(sound)
    except Exception as e:
        _logger.error(f"Error playing audio: {e}", exc_info=True)
        raise


def extract_text_from_response(response) -> str:
    """Extrai texto da resposta OpenAI, garantindo que sempre retorne uma string."""
    if not hasattr(response, "choices") or not response.choices:
        return ""

    message = response.choices[0].message
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        for block in content:
            if block.get("type") == "text":
                return block.get("text", "")

    if content is None and hasattr(message, "audio") and hasattr(message.audio, "transcript"):
        transcript = getattr(message.audio, "transcript", "")
        _logger.info(f"Transcript extracted from message.audio.transcript: {transcript!r}")
        return transcript

    if hasattr(content, "transcript"):
        transcript = getattr(content, "transcript", "")
        _logger.info(f"Transcript extracted from message.content.transcript: {transcript!r}")
        return transcript

    _logger.warning(f"Unexpected content type for message.content: {type(content)}")
    return ""


def extract_audio_from_response(response):
    """Extrai dados de áudio (base64) da resposta OpenAI."""
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        if hasattr(message, "audio") and hasattr(message.audio, "data") and message.audio.data:
            return message.audio.data

    _logger.warning("No audio data found in the response.")
    return None


def encode_file_to_base64(file_path: str) -> str:
    """Reads an audio file and encodes its content to a base64 string."""
    try:
        with open(file_path, "rb") as audio_file:
            return base64.b64encode(audio_file.read()).decode("utf-8")
    except FileNotFoundError as e:
        _logger.error(f"Error encoding to base64: File not found at {file_path}")
        raise e
    except Exception as e:
        _logger.error(f"Error encoding file {file_path} to base64: {e}")
        raise e
