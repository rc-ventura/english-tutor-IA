import logging
import base64
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import (
    extract_audio_from_response,
    extract_text_from_response,
    save_audio_to_temp_file,
)


def play_audio(audio_bytes: bytes) -> None:
    """Legacy no-op for compatibility with older tests."""
    return None


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

        if history is None and isinstance(input_data, list):
            history = input_data
            input_data = None

        if input_data is None:
            if history is None or not history:
                updated_history, _ = self.handle_transcription(audio_filepath=input_data, history=history)
            else:
                updated_history = history
        else:
            updated_history, _ = self.handle_transcription(audio_filepath=input_data, history=history)
        _logger.info(
            f"SpeakingTutor.process_input (synchronous): Start. audio_file_path='{input_data}', level='{level}'"
        )

        # This method's logic remains complex due to its synchronous nature and test dependencies.
        # It's kept for testability, while the UI uses the more granular async-friendly methods.
        final_history, _, _ = self.handle_bot_response(history=updated_history, level=level)

        _logger.info("SpeakingTutor.process_input (synchronous): Finished. Yielding final history.")
        # Yielding a tuple to maintain compatibility with existing tests.
        yield final_history, final_history

    def handle_transcription(
        self,
        history: Optional[List[Dict[str, Any]]],
        audio_filepath: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Transcribes user audio, adds it to history, and returns the updated history for chatbot and state."""
        current_history = history.copy() if history else []
        _logger.info(f"handle_transcription: Start. Received audio: {audio_filepath}, Level: {level}")

        if not audio_filepath:
            _logger.error("No audio filepath provided to handle_transcription.")
            error_message = {
                "role": "assistant",
                "content": "No audio input received",
            }
            if isinstance(current_history, list):
                current_history.append(error_message)
            else:  # Should not happen if type hints are followed
                current_history = [error_message]
            return current_history, current_history

        try:
            _logger.info(f"Transcribing audio from '{audio_filepath}'...")
            user_transcribed_text = self.openai_service.transcribe_audio(audio_filepath)
            if not user_transcribed_text or not user_transcribed_text.strip():
                user_transcribed_text = "[Audio not clear or empty]"
                _logger.warning("Transcription was empty or unclear.")
            _logger.info(f"Transcription successful: '{user_transcribed_text}'")
        except Exception as e:
            _logger.error(f"Error during audio transcription: {e}", exc_info=True)
            error_msg = f"Sorry, couldn't transcribe your audio: {e}"
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
        bot_audio_path: Optional[str] = None,
        delay_text: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """Gets bot response, saves audio, and optionally delays adding text until audio length has elapsed."""
        current_history = history.copy() if history else []
        _logger.info(f"handle_bot_response: Start. History has {len(current_history)} messages.")

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response called with invalid history state. Aborting.")
            return current_history, current_history, None

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)
        messages_for_llm = [{"role": "system", "content": system_prompt}] + current_history

        try:
            _logger.info(f"Sending {len(messages_for_llm)} messages to chat_multimodal.")
            response = self.openai_service.chat_multimodal(messages=messages_for_llm, input_audio_path=None)
            bot_text_response = extract_text_from_response(response)
            _logger.info(f"Extracted bot_text_response: {bot_text_response!r}")
            audio_base64_data = extract_audio_from_response(response)
        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, we encountered an error getting a response: {e}"
            current_history.append({"role": "assistant", "content": error_msg})
            return current_history, current_history, None

        if audio_base64_data:
            _logger.info("Bot audio data found. Saving to temporary file...")
            try:
                audio_bytes = base64.b64decode(audio_base64_data)
                bot_audio_path = save_audio_to_temp_file(audio_bytes)
                _logger.info(f"Bot audio saved to temporary file: {bot_audio_path}")
                play_audio(audio_bytes)
            except Exception as e:
                _logger.error(f"Error decoding or playing bot audio: {e}", exc_info=True)
                error_suffix = " (Error playing audio response)"
                if bot_text_response:
                    bot_text_response += error_suffix
                else:
                    # If bot_text_response was empty, create one with the error
                    bot_text_response = f"[No text response from bot]{error_suffix}"
        else:
            _logger.warning("No bot audio data found in LLM response.")

        if bot_text_response:
            if delay_text and bot_audio_path:
                try:
                    from pydub import AudioSegment
                    import time

                    audio = AudioSegment.from_file(bot_audio_path)
                    duration = len(audio) / 1000.0
                    _logger.info(f"Delaying bot text for {duration:.2f} seconds to match audio length")
                    time.sleep(duration)
                except Exception as e:
                    _logger.error(f"Error loading audio for delay: {e}", exc_info=True)

            current_history.append({"role": "assistant", "content": bot_text_response})

        _logger.info(
            f"handle_bot_response: Finished. History len: {len(current_history)}, Audio path: {bot_audio_path}"
        )
        return current_history, current_history, bot_audio_path
