import logging
import os
from typing import Optional

from dotenv import load_dotenv

from src.core.speaking_tutor import SpeakingTutor
from src.core.writing_tutor import WritingTutor
from src.models.prompts import system_message
from src.services.openai_service import OpenAIService
from ui.interfaces import run_gradio_interface


class EnglishTutor:
    """Main English tutoring system coordinating all components."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._setup()
        if not self.openai_api_key:
            raise ValueError("OpenAI API Key not found in environment")
        self.openai_service = OpenAIService(api_key=self.openai_api_key, model=self.model)
        # Critical initialization
        self.speaking_tutor = SpeakingTutor(self.openai_service, self)
        self.writing_tutor = WritingTutor(self.openai_service, self)

    def set_api_key(self, api_key: str) -> str:
        """Update the API key and reinitialize the OpenAI service."""
        if not api_key:
            return "API key cannot be empty"
        self.openai_api_key = api_key
        self.openai_service = OpenAIService(api_key=api_key, model=self.model)
        self.speaking_tutor.openai_service = self.openai_service
        self.writing_tutor.openai_service = self.openai_service
        return "API key updated"

    def _setup(self) -> None:
        """Initialize configuration."""
        load_dotenv(override=True)
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or ""

    def get_system_message(self, mode: str = "speaking", level: Optional[str] = None) -> str:
        """Get the appropriate system message based on tutoring mode."""
        return system_message(mode, level)

    # instance method
    def main(self):
        """Run the Gradio interface."""
        run_gradio_interface(self)


# module-level function
def main():
    """Entry point for the tutor application."""
    try:
        tutor = EnglishTutor()
        tutor.main()
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Application startup error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
