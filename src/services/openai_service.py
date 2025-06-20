import logging
from typing import Any, Dict, Generator, List

from openai import OpenAI, AuthenticationError
from openai.types.chat import ChatCompletion

# --- Constants for Model Names ---
MULTIMODAL_MODEL = "gpt-4o-mini-audio-preview"
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"


class OpenAIService:
    @staticmethod
    def is_key_valid(api_key: str) -> bool:
        """Checks if the provided OpenAI API key is valid by attempting a lightweight API call."""
        if not api_key:
            return False
        try:
            client = OpenAI(api_key=api_key)
            client.models.list()  # A simple call to check authentication
            return True
        except AuthenticationError:
            logging.warning("Invalid API key provided.")
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
            logging.error(f"OpenAI API error during streaming: {e}", exc_info=True)
            raise

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio using the specified transcription model.
        Returns the transcribed text or raises an exception on error.
        """
        logging.info(f"Transcribing audio file: {audio_file_path}")
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=TRANSCRIPTION_MODEL,
                    file=audio_file,
                    language="en",
                    response_format="text",
                )
            logging.info("Audio transcribed successfully.")
            return transcription
        except Exception as e:
            logging.error(f"OpenAI API error during transcription: {e}", exc_info=True)
            raise
