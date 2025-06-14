import logging
import tempfile

from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

logger = logging.getLogger(__name__)


def talker(text: str, lang: str = "en"):
    """Convert text to speech and play it.

    Args:
        message: Text to convert to speech
    """
    if not text or not text.strip():
        logger.warning("Talker received empty text. Skipping TTS.")
        return

    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_file:
            tts.save(temp_file.name)
            sound = AudioSegment.from_mp3(temp_file.name)
            logger.info(f"Playing TTS for text: '{text[:50]}...'")

            play(sound)
    except Exception as e:
        logger.error(f"Error in TTS talker: {e}", exc_info=True)
        raise  # Or handle more gracefully depending on desired UX
