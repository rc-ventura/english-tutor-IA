import logging
import base64
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import (
    extract_audio_from_response,
    extract_text_from_response,
    play_audio,
)

_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class SpeakingTutor(BaseTutor):
    def process_input(
        self,
        input_data: Optional[str],
        history: Optional[List[Dict[str, Any]]],
        level: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """
        Processes user audio input synchronously, fulfilling the BaseTutor contract.
        This method orchestrates transcription and bot response in a single call.
        The Gradio UI uses handle_transcription and handle_bot_response for a better UX.
        """
        _logger.info(
            f"SpeakingTutor.process_input (synchronous): Start. audio_file_path='{input_data}', level='{level}'"
        )

        # This method's logic remains complex due to its synchronous nature and test dependencies.
        # It's kept for testability, while the UI uses the more granular async-friendly methods.
        updated_history = self.handle_transcription(audio_file_path=input_data, history=history)

        final_history = self.handle_bot_response(history=updated_history, level=level)

        _logger.info("SpeakingTutor.process_input (synchronous): Finished. Yielding final history.")
        # Yielding a tuple to maintain compatibility with existing tests.
        yield final_history, final_history

    def handle_transcription(
        self,
        audio_file_path: Optional[str],
        history: Optional[List[Dict[str, Any]]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Transcribes user audio, adds it to history, and returns the updated history for chatbot and state."""
        current_history = history.copy() if history else []
        _logger.info(f"handle_transcription: Start. audio_file_path='{audio_file_path}'")

        if not audio_file_path:
            _logger.warning("No audio file path provided.")
            return current_history, current_history

        try:
            _logger.info(f"Transcribing audio from '{audio_file_path}'...")
            user_transcribed_text = self.openai_service.transcribe_audio(audio_file_path)
            if not user_transcribed_text or not user_transcribed_text.strip():
                user_transcribed_text = "[Audio not clear or empty]"
                _logger.warning("Transcription was empty or unclear.")
            _logger.info(f"Transcription successful: '{user_transcribed_text}'")
        except Exception as e:
            _logger.error(f"Error during audio transcription: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred during transcription: {e}"
            # Add user's attempt (empty transcription) and then bot's error message
            # current_history.append({"role": "user", "content": "[Audio input processed]"}) # Optional: indicate user action
            current_history.append({"role": "assistant", "content": error_msg})
            return current_history, current_history

        current_history.append({"role": "user", "content": user_transcribed_text})
        _logger.info("handle_transcription: Finished. Returning updated history.")
        return current_history, current_history

    def handle_bot_response(
        self,
        history: Optional[List[Dict[str, Any]]],
        level: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Gets bot response, plays audio, adds text to history, and returns final state for chatbot and state."""
        current_history = history.copy() if history else []
        _logger.info(f"handle_bot_response: Start. History has {len(current_history)} messages.")

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response called with invalid history state. Aborting.")
            return current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)
        messages_for_llm = [{"role": "system", "content": system_prompt}] + current_history

        try:
            _logger.info(f"Sending {len(messages_for_llm)} messages to chat_multimodal.")
            response = self.openai_service.chat_multimodal(messages=messages_for_llm)
            bot_text_response = extract_text_from_response(response)
            _logger.info(f"Extracted bot_text_response: {bot_text_response!r}")
            audio_base64_data = extract_audio_from_response(response)
        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred: {e}"
            current_history.append({"role": "assistant", "content": error_msg})
            return current_history, current_history

        if audio_base64_data:
            _logger.info("Bot audio found. Playing audio before showing text...")
            try:
                audio_bytes = base64.b64decode(audio_base64_data)
                play_audio(audio_bytes)
                _logger.info("Finished playing bot audio.")
            except Exception as e:
                _logger.error(f"Error during blocking audio playback: {e}", exc_info=True)
                bot_text_response += " (Error playing audio)"
        else:
            _logger.warning("No bot audio found in LLM response.")

        if bot_text_response:
            current_history.append({"role": "assistant", "content": bot_text_response})

        _logger.info(f"handle_bot_response: Finished. History len: {len(current_history)}")
        return current_history, current_history
