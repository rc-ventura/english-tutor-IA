from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple

from src.services.openai_service import OpenAIService

if TYPE_CHECKING:
    from src.core.tutor import EnglishTutor


class BaseTutor(ABC):
    def __init__(self, openai_service: OpenAIService, tutor_parent: "EnglishTutor"):
        self.openai_service = openai_service
        self.tutor_parent = tutor_parent

    @abstractmethod
    def process_input(
        self,
        input_data: Any | None = None,
        history: Optional[List[Dict[str, Any]]] = None,
        level: Optional[str] = None,
        speaking_mode: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Process user input and return chatbot messages and updated history."""
