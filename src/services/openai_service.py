import logging
import os
import tempfile
import shutil
from typing import Optional
from openai import OpenAI

class OpenAIService:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def get_chat_completion(self, messages: list):
        """Handle chat completion requests."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return response
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            raise
            
    def transcribe_audio(self, audio_file) -> str:
        """Transcribe audio using Whisper.
        Returns the transcribed text or empty string on error/cancel."""
        if not audio_file:
            return ""
            
        try:
            if isinstance(audio_file, str):
                if not os.path.isfile(audio_file):
                    return ""
                with open(audio_file, "rb") as f:
                    if f.read(4) != b'RIFF':
                        return ""
                    f.seek(0)
                    result = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language="en"
                    )
            else:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    shutil.copyfileobj(audio_file, temp_file)
                    temp_path = temp_file.name
                
                try:
                    with open(temp_path, "rb") as f:
                        result = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f,
                            language="en"
                        )
                finally:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                        
            return result.text.strip() if hasattr(result, 'text') else ""
            
        except Exception:
            return ""
