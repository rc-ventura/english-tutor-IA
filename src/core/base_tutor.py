from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
from src.services.openai_service import OpenAIService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor

class BaseTutor(ABC):
    def __init__(self, openai_service: OpenAIService, tutor_parent: 'EnglishTutor'):
        self.openai_service = openai_service
        self.tutor_parent = tutor_parent


    @abstractmethod
    def process_input(self, input_data: Any, history: List[Dict], level: Optional[str] = None) -> tuple[List[Dict], List[Dict]]:
        """Process user input and return chatbot messages and updated history."""
        pass