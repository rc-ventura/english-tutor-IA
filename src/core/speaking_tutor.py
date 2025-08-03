import base64
import logging
import time
import os
import gradio as gr
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
        speaking_mode: Optional[str] = None,
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
        speaking_mode: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Transcribes user audio, adds it to history, and returns the updated history."""
        current_history = history.copy() if history else []

        if not self.tutor_parent.openai_service:
            error_message = {
                "role": "assistant",
                "content": "⚠️ No valid OpenAI API key set. Please enter your API key in the settings.",
            }
            current_history.append(error_message)
            return current_history, current_history

        if not audio_filepath or not os.path.exists(audio_filepath):
            _logger.warning("Audio file not provided or does not exist.")
            return current_history, current_history

        # Check if the audio file is too small (likely an empty recording)
        min_audio_size_bytes = 1024  # 1 KB
        if os.path.getsize(audio_filepath) < min_audio_size_bytes:
            _logger.error(f"Audio file at {audio_filepath} is too small, likely an empty recording.")
            error_message = {
                "role": "assistant",
                "content": "It seems the audio was empty. Please try recording again.",
            }
            current_history.append(error_message)
            return current_history, current_history

        try:
            transcription = self.tutor_parent.openai_service.transcribe_audio(audio_filepath)
            if speaking_mode == "Immersive":
                user_message = {"role": "user", "content": (audio_filepath, None), "text_for_llm": transcription}
            else:
                user_message = {"role": "user", "content": transcription}

            current_history.append(user_message)
            return current_history, current_history
        except Exception as e:
            error_message = {"role": "assistant", "content": f"Error transcribing audio: {str(e)}"}
            current_history.append(error_message)
            return current_history, current_history

    def handle_bot_response(
        self,
        history: Optional[List[Dict[str, Any]]],
        level: Optional[str] = None,
        speaking_mode: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]], None, None]:
        """
        Gets bot response, yields audio for immediate playback, waits for it to finish,
        then yields the updated chat history with the bot's text.
        """
        if not self.tutor_parent.openai_service:
            yield gr.Error("No valid OpenAI API key set. Please enter your API key in the settings."), [], None
            return

        current_history = history.copy() if history else []
        _logger.info(f"handle_bot_response: Start. History has {len(current_history)} messages.")

        if not current_history or current_history[-1].get("role") != "user":
            _logger.warning("handle_bot_response called with invalid history state. Aborting.")

            yield current_history, current_history, None

            return

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)

        # Sanitize history to prevent audio generation bugs.
        messages_for_llm = []
        for message in current_history:
            llm_message = {"role": message["role"]}
            if "text_for_llm" in message:
                llm_message["content"] = message["text_for_llm"]
            else:
                llm_message["content"] = message["content"]
            messages_for_llm.append(llm_message)

        messages_for_llm = [{"role": "system", "content": system_prompt}] + messages_for_llm

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

            if speaking_mode == "Immersive":
                # In immersive mode, just add the audio player to the chat
                _logger.info("Immersive mode: Yielding audio for playback.")
                bot_message = {
                    "role": "assistant",
                    "content": (audio_path, None),
                    "text_for_llm": bot_text_response,
                }
                current_history.append(bot_message)
                yield current_history, current_history, audio_path
                return

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
                yield current_history, current_history, None  # audio_path

                # Control the streaming speed for a natural feel
                time.sleep(0.05)

        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred while I was thinking. Please try again."

            current_history.append({"role": "assistant", "content": error_msg})

            yield current_history, current_history, None
