import logging
import os
import shutil
from typing import Any, Dict, Generator, List
from src.models.prompts import TRANSCRIBE_PROMPT

from openai import OpenAI, AuthenticationError
from pydub import AudioSegment
from openai.types.chat import ChatCompletion

# --- Constants for Model Names (configurable via env) ---
MULTIMODAL_MODEL = os.getenv("MULTIMODAL_MODEL", "gpt-4o-mini-audio-preview")
TRANSCRIPTION_MODEL = os.getenv("TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
FALLBACK_TRANSCRIPTION_MODEL = os.getenv("FALLBACK_TRANSCRIPTION_MODEL", "Whisper-1")

logging.info(
    f"Using models: MULTIMODAL_MODEL={MULTIMODAL_MODEL}, TRANSCRIPTION_MODEL={TRANSCRIPTION_MODEL}, FALLBACK_TRANSCRIPTION_MODEL={FALLBACK_TRANSCRIPTION_MODEL}"
)


class OpenAIService:
    @staticmethod
    def is_key_valid(api_key: str) -> bool:
        """Checks if the provided OpenAI API key is valid by attempting a lightweight API call."""
        if not api_key or not api_key.strip():
            return False

        if not api_key.startswith("sk-"):
            return False
        try:
            client = OpenAI(api_key=api_key)
            client.models.list()  # A simple call to check authentication

            return True

        except AuthenticationError:
            logging.warning("Invalid API key provided (AuthenticationError)")
            return False

        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                logging.warning(f"Authentication failed: {e}")
                return False
            else:
                logging.warning(f"API validation error: {e}")
                return False

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("API key is required for OpenAIService.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat_multimodal(
        self,
        messages: List[Dict[str, Any]],
        voice: str = "alloy",
        output_format: str = "wav",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> ChatCompletion:
        """
        Sends messages to OpenAI's multimodal model and requests both text and audio.
        The caller is responsible for formatting the 'messages' payload correctly.
        """
        if not messages:
            logging.error("'messages' must be a non-empty list.")
            raise ValueError("Messages list cannot be empty for chat_multimodal")

        logging.info(f"Sending {len(messages)} messages to multimodal model {MULTIMODAL_MODEL}.")

        response = self.client.chat.completions.create(
            model=MULTIMODAL_MODEL,
            modalities=["text", "audio"],
            audio={"voice": voice, "format": output_format},
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Generator[str, None, None]:
        """Stream chat completion tokens one by one."""
        logging.info(f"Requesting streaming chat completion with model {self.model}.")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logging.error(f"Error during multimodal chat: {e}", exc_info=True)
            raise

    def text_to_speech(self, text: str, model: str = "tts-1", voice: str = "alloy") -> bytes:
        """Converts text to speech using OpenAI's TTS model and returns the audio data as bytes."""
        if not self.client:
            logging.error("OpenAI client is not initialized. Cannot perform text-to-speech.")
            raise ConnectionError("OpenAI client not initialized. Please set a valid API key.")

        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
            )
            # The response contains the audio data directly.
            return response.content
        except Exception as e:
            logging.error(f"Error during text-to-speech generation: {e}", exc_info=True)
            raise

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio using the specified transcription model.
        It uses pydub to convert the input audio to a valid WAV format first,
        ensuring compatibility with OpenAI's API and handling potentially corrupted files.
        """
        logging.info(f"Received audio for transcription: {audio_file_path}")
        converted_wav_path = audio_file_path + ".wav"

        try:
            # Convert the input audio file to WAV format using pydub
            # This handles various input formats and fixes potential corruption.
            audio = AudioSegment.from_file(audio_file_path)
            audio.export(converted_wav_path, format="wav")
            logging.info(f"Successfully converted audio to WAV: {converted_wav_path}")

            # Basic integrity check on the converted file
            try:
                size_bytes = os.path.getsize(converted_wav_path)
                logging.info(f"Converted WAV size: {size_bytes} bytes")
                if size_bytes < 1024:  # < 1KB usually indicates empty/invalid file
                    raise ValueError("Converted WAV appears too small; possible empty/invalid recording.")
            except Exception as size_err:
                logging.error(f"Converted WAV size check failed: {size_err}")
                raise

            # Transcribe the converted WAV file
            def _do_transcribe(model_name: str) -> str:
                logging.info(f"Transcribing with model: {model_name}")
                with open(converted_wav_path, "rb") as audio_file:
                    resp = self.client.audio.transcriptions.create(
                        model=model_name,
                        file=audio_file,
                        language="en",
                        # Avoid response_format="text" to prevent JSON parse errors in SDK
                        prompt=TRANSCRIBE_PROMPT,
                    )
                # The SDK returns an object with .text
                if hasattr(resp, "text") and isinstance(resp.text, str):
                    return resp.text
                # Some SDKs might return the raw string
                if isinstance(resp, str):
                    return resp
                # Last resort, try to get any plausible text field
                if hasattr(resp, "output_text"):
                    return getattr(resp, "output_text")
                raise ValueError("Unexpected transcription response type; no text found.")

            try:
                text = _do_transcribe(TRANSCRIPTION_MODEL)
            except Exception as primary_err:
                logging.error(f"Primary transcription failed ({TRANSCRIPTION_MODEL}): {primary_err}", exc_info=True)
                logging.info(f"Falling back to {FALLBACK_TRANSCRIPTION_MODEL}...")
                text = _do_transcribe(FALLBACK_TRANSCRIPTION_MODEL)

            logging.info("Audio transcribed successfully.")
            return text

        except Exception as e:
            logging.error(f"Error during audio conversion or transcription: {e}", exc_info=True)
            # Re-raise the exception to be handled by the calling function
            raise

        finally:
            # Clean up the converted WAV file
            if os.path.exists(converted_wav_path):
                os.remove(converted_wav_path)
                logging.info(f"Removed temporary WAV file: {converted_wav_path}")
