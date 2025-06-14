import logging
from typing import Optional, Dict
from openai import OpenAI

class OpenAIService:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("API key is required for OpenAIService.")
       
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logging.basicConfig(level=logging.INFO)

        
    def get_chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict:
        """Handle chat completion requests."""
        
        logging.info(f"Requesting chat completion with model {self.model} for {len(messages)} messages.")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logging.info("Chat completion received successfully.")
            return response
        except Exception as e:
            logging.error(f"OpenAI API error during chat completion: {e}", exc_info=True)
            raise

    def stream_chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Stream chat completion tokens one by one."""

        logging.info(
            f"Requesting streaming chat completion with model {self.model} for {len(messages)} messages."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logging.error(
                f"OpenAI API error during streaming chat completion: {e}",
                exc_info=True,
            )
            raise
            
    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using Whisper.
        Returns the transcribed text or empty string on error/cancel."""
        
        logging.info(f"Transcribing audio file: {audio_file_path}")
        try:

            with open(audio_file_path, "rb") as audio_file:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"

                )
                
            logging.info("Audio transcribed successfully.")
            # The OpenAI client returns a Transcription object; extract the text
            return result.text if hasattr(result, "text") else str(result)
                
        except Exception as e:
            logging.error(f"OpenAI API error during audio transcription: {e}", exc_info=True)
            raise
