
from io import BytesIO
import threading
import os
import logging
from typing import Optional, Tuple
from pydub import AudioSegment
from pydub.playback import play
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_audio(audio_file, tutor) -> Tuple[str, None]:
    """Process audio file for transcription.
    Returns (transcription_text, None) or ("", None) on error/cancel"""
    if not audio_file:
        return "", None
    
    try:
        # Get file path from dict or use as is
        audio_path = audio_file.get("path") if isinstance(audio_file, dict) else str(audio_file)
        
        if not audio_path or not os.path.isfile(audio_path):
            return "", None
            
        # Get transcription and clean up
        transcription = tutor.transcript_audio(audio_path)
        try:
            os.remove(audio_path)
        except:
            pass
            
        return str(transcription or ""), None
        
    except Exception:
        return "", None

def talker(message: str) -> None:
    """Convert text to speech and play it.
    
    Args:
        message: Text to convert to speech
    """
    try:
        response = openai.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=message,
        )

        audio_stream = BytesIO(response.content)
        audio = AudioSegment.from_file(audio_stream, format="mp3")
        threading.Thread(target=play, args=(audio,), daemon=True).start()
    
    except Exception as e:
        logging.error(f"Error in talker: {e}")