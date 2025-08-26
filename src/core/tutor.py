import logging
import os
import uvicorn
from typing import Optional

from dotenv import load_dotenv

from src.core.speaking_tutor import SpeakingTutor
from src.core.writing_tutor import WritingTutor
from src.models.prompts import system_message
from src.services.openai_service import OpenAIService
from src.core.progress_tracker import ProgressTracker
from ui.interfaces import run_gradio_interface
from src.infra.telemetry import TelemetryService


class EnglishTutor:
    """Main English tutoring system coordinating all components."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.progress_tracker = ProgressTracker()
        self._setup()

        # Initialize telemetry (best-effort)
        try:
            self.telemetry = TelemetryService(base_dir=os.getenv("TELEMETRY_DIR"))
        except Exception:
            self.telemetry = None

        try:
            self.openai_service = OpenAIService(api_key=self.openai_api_key, model=self.model, telemetry=self.telemetry)
        except ValueError as e:
            logging.warning(f"OpenAIService could not be initialized: {e}. API key might need to be set via UI.")
            self.openai_service = None

        if not self.openai_api_key:
            logging.warning(
                "OpenAI API Key not found in environment during Tutor init. User may need to set it in the UI."
            )

        self.speaking_tutor = SpeakingTutor(self.openai_service, self)
        self.writing_tutor = WritingTutor(self.openai_service, self)

    def set_api_key(self, api_key: str) -> str:
        """Update the API key, validate it, and reinitialize the OpenAI service. Returns a message indicating success or failure."""

        current_api_key_attempt = api_key

        if not api_key or not api_key.strip():
            self.openai_service = None

            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None

            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None

            return "⚠️  API key cannot be empty or contain only whitespace."

        if not OpenAIService.is_key_valid(api_key):
            self.openai_api_key = current_api_key_attempt
            self.openai_service = None

            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None

            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None

            return "❌ Invalid OpenAI API key. Please check the key and try again."

        try:
            self.openai_api_key = api_key
            self.openai_service = OpenAIService(api_key=self.openai_api_key, model=self.model, telemetry=self.telemetry)

            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = self.openai_service

            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = self.openai_service

            return "✅ API key set successfully!"

        except Exception as e:
            self.openai_api_key = current_api_key_attempt
            self.openai_service = None

            if hasattr(self, "speaking_tutor") and self.speaking_tutor:
                self.speaking_tutor.openai_service = None

            if hasattr(self, "writing_tutor") and self.writing_tutor:
                self.writing_tutor.openai_service = None

            return f"🚫 Falha ao inicializar o serviço OpenAI: {e}"

    def _setup(self) -> None:
        """Initialize configuration."""
        load_dotenv(override=True)
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or ""
        if self.openai_api_key:
            if OpenAIService.is_key_valid(self.openai_api_key):
                self.api_key_status = "✅ API key set successfully!"
            else:
                self.api_key_status = "🚫 Invalid API key found in environment."
        else:
            self.api_key_status = "⚠️ No API key found. Please enter your OpenAI API key."

    def get_system_message(self, mode: str = "speaking", level: Optional[str] = None) -> str:
        """Get the appropriate system message based on tutoring mode."""
        return system_message(mode, level)

    def launch_ui(self):
        """Run the Gradio interface."""
        app = run_gradio_interface(self)
        uvicorn.run(app, host="127.0.0.1", port=7901, log_level="info")


# Ensure INFO-level logs are visible for our modules (diagnostics, summary injection/updates)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s", force=True)


# module-level function
def main():
    """Entry point for the tutor application."""
    try:
        tutor = EnglishTutor()
        tutor.launch_ui()
    except Exception as e:
        logging.error(f"Application startup error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
