import logging
import os
import uvicorn
from typing import Optional

from dotenv import load_dotenv

# Forward declaration for type hinting if GradioInterface is in tutor.py
# However, run_gradio_interface is imported from ui.interfaces, so direct Gradio import is not needed here.

from src.core.speaking_tutor import SpeakingTutor
from src.core.writing_tutor import WritingTutor
from src.models.prompts import system_message
from src.services.openai_service import OpenAIService
from src.core.progress_tracker import ProgressTracker
from ui.interfaces import run_gradio_interface  # This implies Gradio is handled in ui.interfaces


class EnglishTutor:
    """Main English tutoring system coordinating all components."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        # Initialize user progress tracking
        self.progress_tracker = ProgressTracker()
        self._setup()  # This will load openai_api_key from .env if present

        # Initialize openai_service. If key is missing, it might be set later via UI.
        # OpenAIService itself will raise ValueError if api_key is truly empty at the point of its use.
        # We allow initialization with an empty key here, UI will handle prompting if needed.
        try:
            self.openai_service = OpenAIService(api_key=self.openai_api_key, model=self.model)
        except ValueError as e:
            logging.warning(f"OpenAIService could not be initialized: {e}. API key might need to be set via UI.")
            # Potentially set a flag or a placeholder service if needed, or handle in UI
            self.openai_service = None  # Or a dummy service that indicates key is needed

        if not self.openai_api_key:
            logging.warning(
                "OpenAI API Key not found in environment during Tutor init. User may need to set it in the UI."
            )

        # Initialize tutors. They will use self.openai_service which might be None initially.
        # Their methods should handle cases where openai_service is not ready.
        self.speaking_tutor = SpeakingTutor(self.openai_service, self)
        self.writing_tutor = WritingTutor(self.openai_service, self)

    def set_api_key(self, api_key: str) -> None:
        """Update the API key, validate it, and reinitialize the OpenAI service. Raises ValueError if the key is invalid."""
        current_api_key_attempt = api_key  # Store the attempt for logging or state if needed

        if not api_key or not api_key.strip():
            self.openai_service = None
            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None
            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None
            # self.openai_api_key = "" # Optionally clear stored key
            raise ValueError("API key cannot be empty or just whitespace.")

        if not OpenAIService.is_key_valid(api_key):
            self.openai_api_key = current_api_key_attempt
            self.openai_service = None
            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None
            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None
            # is_key_valid already logs a warning from OpenAIService
            raise ValueError("Invalid OpenAI API key provided. Please check the key and try again.")

        try:
            self.openai_api_key = api_key  # Set the valid key
            self.openai_service = OpenAIService(api_key=self.openai_api_key, model=self.model)
            # Update tutors with the new service instance
            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = self.openai_service
            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = self.openai_service
        except Exception as e:  # Catch any unexpected error during OpenAIService init
            self.openai_api_key = current_api_key_attempt  # Store the key that failed init
            self.openai_service = None
            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None
            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None
            logging.error(f"Failed to initialize OpenAIService with a key that was deemed valid: {e}", exc_info=True)
            raise ValueError(f"Failed to initialize OpenAI service, though the key appeared valid: {e}")

    def _setup(self) -> None:
        """Initialize configuration."""
        load_dotenv(override=True)
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or ""

    def get_system_message(self, mode: str = "speaking", level: Optional[str] = None) -> str:
        """Get the appropriate system message based on tutoring mode."""
        return system_message(mode, level)

    def launch_ui(self):
        """Run the Gradio interface."""
        app = run_gradio_interface(self)
        uvicorn.run(app, host="127.0.0.1", port=7901)


# module-level function
def main():
    """Entry point for the tutor application."""
    try:
        tutor = EnglishTutor()
        tutor.launch_ui()
    except Exception as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Application startup error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
