import logging
import base64
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import (
    extract_audio_from_response,
    extract_text_from_response,
    save_audio_to_temp_file,
)

# Stub functions used by tests
def play_audio(audio_bytes: bytes) -> None:
    """Play audio data (placeholder for tests)."""
    pass


def talker(*args, **kwargs) -> None:
    """Placeholder talker function for tests."""
    pass

# Gradio's special value to indicate no update. Provide a fallback for tests.
try:  # pragma: no cover - optional import for runtime only
    import gradio as gr
    NO_AUDIO_UPDATE = gr.update()
except Exception:  # pragma: no cover - tests don't require gradio
    class _NoUpdate:
        pass

    NO_AUDIO_UPDATE = _NoUpdate()

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
        updated_history, _ = self.handle_transcription(audio_filepath=input_data, history=history)

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
            # Attempt to add an error message to the chat history
            # This might not be the best place if history is not reliably passed or returned
            # but let's try for now.
            error_message = {
                "role": "assistant",
                "content": "Error: No audio data was recorded or sent. Please try again.",
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
            error_msg = f"Sorry, an error occurred during transcription: {e}"
            # Add user's attempt (empty transcription) and then bot's error message
            # current_history.append({"role": "user", "content": "[Audio input processed]"}) # Optional: indicate user action
            current_history.append({"role": "assistant", "content": error_msg})
            return current_history, current_history

        current_history.append({"role": "user", "content": user_transcribed_text})
        _logger.info("handle_transcription: Finished. Returning updated history.")
        return current_history, current_history

    def handle_bot_response(
        self, history: Optional[List[Dict[str, Any]]], level: Optional[str] = None, bot_audio_path: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """Gets bot response, saves audio, adds text to history, and returns final state and audio path."""
        current_history = history.copy() if history else []
        _logger.info(f"handle_bot_response: Start. History has {len(current_history)} messages.")

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response called with invalid history state. Aborting.")
            return current_history, current_history, None

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
            return current_history, current_history, None

        if audio_base64_data:
            _logger.info("Bot audio data found. Saving to temporary file...")
            try:
                audio_bytes = base64.b64decode(audio_base64_data)
                bot_audio_path = save_audio_to_temp_file(audio_bytes)
                _logger.info(f"Bot audio saved to temporary file: {bot_audio_path}")
                try:
                    play_audio(audio_bytes)
                except Exception as e:
                    _logger.error(f"Error playing audio: {e}", exc_info=True)
                    bot_text_response += " (Error playing audio response)"
            except Exception as e:
                _logger.error(f"Error decoding or saving bot audio: {e}", exc_info=True)
                # Append error to text response if audio processing fails
                error_suffix = " (Error processing audio data)"
                if bot_text_response:
                    bot_text_response += error_suffix
                else:
                    # If bot_text_response was empty, create one with the error
                    bot_text_response = f"[No text response from bot]{error_suffix}"
        else:
            _logger.warning("No bot audio data found in LLM response.")

        if bot_text_response:
            current_history.append({"role": "assistant", "content": bot_text_response})

        _logger.info(
            f"handle_bot_response: Finished. History len: {len(current_history)}, Audio path: {bot_audio_path}"
        )
        return current_history, current_history, bot_audio_path

    def handle_bot_response_streaming(
        self,
        history: Optional[List[Dict[str, Any]]],
        level: Optional[str] = None,
        bot_audio_path: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]], None, None]:
        """Stream assistant reply: yield audio first then text chunks."""

        current_history = history.copy() if history else []
        _logger.info(
            f"handle_bot_response_streaming: Start. History has {len(current_history)} messages."
        )

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response_streaming called with invalid history state. Aborting.")
            yield current_history, current_history, None
            return

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)
        messages_for_llm = [{"role": "system", "content": system_prompt}] + current_history

        try:
            _logger.info(f"Sending {len(messages_for_llm)} messages to chat_multimodal.")
            response = self.openai_service.chat_multimodal(messages=messages_for_llm)
            bot_text_response = extract_text_from_response(response)
            audio_base64_data = extract_audio_from_response(response)
        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred: {e}"
            current_history.append({"role": "assistant", "content": error_msg})
            yield current_history, current_history, None
            return

        if audio_base64_data:
            try:
                audio_bytes = base64.b64decode(audio_base64_data)
                bot_audio_path = save_audio_to_temp_file(audio_bytes)
                try:
                    play_audio(audio_bytes)
                except Exception as e:  # pragma: no cover
                    _logger.error(f"Error playing audio: {e}", exc_info=True)
                    bot_text_response += " (Error playing audio response)"
            except Exception as e:
                _logger.error(f"Error decoding or saving bot audio: {e}", exc_info=True)
                error_suffix = " (Error processing audio data)"
                if bot_text_response:
                    bot_text_response += error_suffix
                else:
                    bot_text_response = f"[No text response from bot]{error_suffix}"
        else:
            _logger.warning("No bot audio data found in LLM response.")

        assistant_message = {"role": "assistant", "content": ""}
        current_history.append(assistant_message)

        # yield audio first
        yield current_history, current_history, bot_audio_path

        reply_buffer = ""
        try:
            for chunk in self.openai_service.stream_chat_completion(messages=messages_for_llm):
                reply_buffer += chunk
                assistant_message["content"] = reply_buffer
                yield current_history, current_history, NO_AUDIO_UPDATE
        except Exception as e:  # pragma: no cover
            _logger.error(f"Error during text streaming: {e}", exc_info=True)
            if not reply_buffer:
                assistant_message["content"] = f"Sorry, an error occurred: {e}"
                yield current_history, current_history, NO_AUDIO_UPDATE

        if not reply_buffer:
            assistant_message["content"] = bot_text_response
            yield current_history, current_history, NO_AUDIO_UPDATE

        _logger.info(
            f"handle_bot_response_streaming: Finished. History len: {len(current_history)}, Audio path: {bot_audio_path}"
        )
