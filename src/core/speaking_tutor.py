import base64
import logging
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import (
    extract_audio_from_response,
    extract_text_from_response,
    get_audio_duration,
    save_audio_to_temp_file,
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

        updated_history = self.handle_transcription(audio_file_path=input_data, history=history)

        final_history = self.handle_bot_response(history=updated_history, level=level)

        _logger.info("SpeakingTutor.process_input (synchronous): Finished. Yielding final history.")
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
                "content": "Error: No audio data was recorded or sent. Please try again.",
            }
            if isinstance(current_history, list):
                current_history.append(error_message)
            else:
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

            current_history.append({"role": "assistant", "content": error_msg})
            return current_history, current_history

        current_history.append({"role": "user", "content": user_transcribed_text})
        _logger.info("handle_transcription: Finished. Returning updated history.")
        return current_history, current_history

    def handle_bot_response(
        self, history: Optional[List[Dict[str, Any]]], level: Optional[str] = None
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]], None, None]:
        """
        Gets bot response, yields audio for immediate playback, waits for it to finish,
        then yields the updated chat history with the bot's text.
        """
        current_history = history.copy() if history else []
        _logger.info(f"handle_bot_response: Start. History has {len(current_history)} messages.")

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response called with invalid history state. Aborting.")
            yield current_history, current_history, None
            return

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)

        # Sanitize history to prevent audio generation bugs.
        sanitized_history = []
        last_assistant_idx = -1
        for i in range(len(current_history) - 1, -1, -1):
            if current_history[i].get("role") == "assistant":
                last_assistant_idx = i
                break
        for i, message in enumerate(current_history):
            if message.get("role") == "user" or i == last_assistant_idx:
                sanitized_history.append(message)

        messages_for_llm = [{"role": "system", "content": system_prompt}] + sanitized_history

        try:
            _logger.info(f"Sending {len(messages_for_llm)} messages to chat_multimodal.")
            response = self.tutor_parent.openai_service.chat_multimodal(messages=messages_for_llm, voice="alloy")

            bot_text_response = extract_text_from_response(response)
            audio_base64_data = extract_audio_from_response(response)

            if not audio_base64_data:
                _logger.warning("No audio data in first response. Retrying...")
                response = self.tutor_parent.openai_service.chat_multimodal(messages=messages_for_llm, voice="alloy")
                bot_text_response = extract_text_from_response(response)
                audio_base64_data = extract_audio_from_response(response)

            if not bot_text_response or not audio_base64_data:
                _logger.error("Failed to get bot response or audio even after retry.")
                error_msg = "I'm sorry, I couldn't generate a response."
                current_history.append({"role": "assistant", "content": error_msg})
                yield current_history, current_history, None
                return

            # --- Audio-First UX Implementation ---
            audio_bytes = base64.b64decode(audio_base64_data)
            audio_path = save_audio_to_temp_file(audio_bytes)

            # 1. Yield audio for immediate playback, without updating the chat text.
            _logger.info("Audio-first UX: Yielding audio for playback.")
            yield current_history, current_history, audio_path

            # 2. Wait for the audio to finish playing before showing the text.
            duration = get_audio_duration(audio_path)
            # Add a small buffer to the wait time
            wait_time = duration + 0.2
            _logger.info(f"Audio-first UX: Waiting for {wait_time:.2f}s for audio to play.")
            time.sleep(wait_time)

            # 3. Now, simulate the streaming of the bot's text.
            _logger.info("Audio-first UX: Simulating text stream.")
            bot_full_text = bot_text_response

            # Add an empty message bubble for the assistant to stream into.
            current_history.append({"role": "assistant", "content": ""})

            words = bot_full_text.split()
            for i, word in enumerate(words):
                # Update the content of the last message
                current_history[-1]["content"] += word + " "

                # Yield the updated state to the UI
                yield current_history, current_history, audio_path

                # Control the streaming speed for a natural feel
                time.sleep(0.05)

        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred while I was thinking. Please try again."

            current_history.append({"role": "assistant", "content": error_msg})

            yield current_history, current_history, None
