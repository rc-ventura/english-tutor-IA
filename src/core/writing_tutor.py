import logging
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor


class WritingTutor(BaseTutor):
    def _stream_response_to_history(
        self,
        messages: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Helper to stream LLM response and update history, yielding for chatbot and state."""
        assistant_message = {"role": "assistant", "content": ""}
        history.append(assistant_message)
        yield history, history  # Yield with the empty message box first

        try:
            reply_buffer = ""
            for chunk in self.openai_service.stream_chat_completion(messages=messages):
                reply_buffer += chunk
                assistant_message["content"] = reply_buffer
                yield history, history
        except Exception as e:
            logging.error(f"OpenAI chat completion error: {e}", exc_info=True)
            assistant_message["content"] = f"Sorry, an error occurred: {e}"
            yield history, history

    def process_input(
        self,
        input_data: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        level: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Evaluates an essay and streams the feedback into the chat history."""
        current_history = history.copy() if history else []

        if not input_data or not input_data.strip():
            current_history.append({"role": "assistant", "content": "No essay provided."})
            yield current_history, current_history
            return

        user_message_content = f"Please evaluate this essay for a {level} level student:\n\n{input_data}"
        current_history.append({"role": "user", "content": user_message_content})
        yield current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        messages = [{"role": "system", "content": system_prompt}] + current_history

        yield from self._stream_response_to_history(messages, current_history)

    def generate_random_topic(
        self,
        level: Optional[str] = None,
        history: Optional[List[Dict]] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Generates a random essay topic and streams it into the chat history."""
        current_history = history.copy() if history else []

        user_request_message = f"Can you give me an essay topic for level {level}?"
        current_history.append({"role": "user", "content": user_request_message})
        yield current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        prompt_for_llm = f"Generate a topic for a writing essay for a student with the level of {level}. Also, suggest structure and number of lines and number of words expectation."
        messages_for_topic = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_for_llm},
        ]

        yield from self._stream_response_to_history(messages_for_topic, current_history)
