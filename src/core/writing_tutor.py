import logging
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import save_audio_to_temp_file


class WritingTutor(BaseTutor):
    def _stream_response_to_history(
        self,
        messages: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Helper to stream LLM response and update history, yielding for chatbot and state."""

        assistant_message = {"role": "assistant", "content": ""}
        history.append(assistant_message)

        yield history, history

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
        writing_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Evaluates an essay and streams the feedback into the chat history."""

        current_history = history.copy() if history else []

        if not input_data or not input_data.strip():
            current_history.append({"role": "assistant", "content": "No essay provided."})

            yield current_history, current_history
            return

        user_message_content = f"Please evaluate this {writing_type} for a {level} level student:\n\n{input_data}"
        current_history.append({"role": "user", "content": user_message_content})

        # --- Progress Tracking ---

        if self.tutor_parent and hasattr(self.tutor_parent, "progress_tracker"):
            # Award 20 XP per essay evaluation and count one task
            self.tutor_parent.progress_tracker.add_xp(20)
            self.tutor_parent.progress_tracker.increment_tasks()

        yield current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        messages = [{"role": "system", "content": system_prompt}] + current_history

        yield from self._stream_response_to_history(messages, current_history)

    def generate_random_topic(
        self,
        level: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        writing_type: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Generates a random essay topic and streams it into the chat history."""

        current_history = history.copy() if history else []

        user_request_message = f"Can you give me an essay topic for level {level} referring to {writing_type}."
        current_history.append({"role": "user", "content": user_request_message})

        yield current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        prompt_for_llm = f"Generate a topic for a writing essay for a student with the level of {level}. Anayze also the writing type {writing_type}. Suggest structure and number of lines and number of words expectation."

        messages_for_topic = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_for_llm},
        ]

        yield from self._stream_response_to_history(messages_for_topic, current_history)

    def play_audio(self, history: List[Dict[str, str]]) -> str | None:
        """
        Takes the last assistant message from the history, converts it to speech,
        and returns the path to the audio file for Gradio to play.
        """
        if not history or not isinstance(history, list):
            logging.warning("play_audio called with empty or invalid history.")
            return None

        last_assistant_message = next((m for m in reversed(history) if m.get("role") == "assistant"), None)

        if not last_assistant_message:
            logging.info("No assistant message found in history, no audio to play.")
            return None

        text_to_speak = last_assistant_message.get("content")
        if not text_to_speak:
            logging.warning("Assistant message is empty, nothing to speak.")
            return None

        if not self.openai_service:
            logging.error("OpenAI service not available in WritingTutor for text-to-speech.")
            return None

        try:
            logging.info(f"Generating audio for feedback: '{text_to_speak[:70]}...'")
            audio_bytes = self.openai_service.text_to_speech(text_to_speak)

            tmp_path = save_audio_to_temp_file(audio_bytes)

            return tmp_path

        except Exception as e:
            logging.error(f"Failed to generate or save audio feedback: {e}", exc_info=True)
            return None
