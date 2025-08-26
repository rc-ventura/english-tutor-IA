import base64
import logging
import time
import os
import threading
import queue
import gradio as gr
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import (
    extract_audio_from_response,
    extract_text_from_response,
    get_audio_duration,
    save_audio_to_temp_file,
)
from src.infra.streaming_manager import StreamingManager

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

        updated_history = self.handle_transcription(audio_filepath=input_data, history=history)

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

        # Prune history to avoid context overflow (system prompt + last N messages)
        max_hist = int(os.getenv("SPEAKING_MAX_HISTORY", "12"))
        if len(messages_for_llm) > max_hist + 1:
            messages_for_llm = [messages_for_llm[0]] + messages_for_llm[-max_hist:]
        total_chars = sum(len(str(m.get("content", ""))) for m in messages_for_llm)
        _logger.info(f"LLM payload pruned to {len(messages_for_llm)} msgs, ~{total_chars} chars.")

        # Inject running summary if available to maintain long-term context
        running_summary = getattr(self, "_running_summary", "")
        if running_summary:
            summary_msg = (
                "Conversation summary so far (for continuity; do not repeat details, use as context only):\n"
                + running_summary
            )
            messages_for_llm = [{"role": "system", "content": summary_msg}] + messages_for_llm
            _logger.info("Summary injected: True, summary_len=%d", len(running_summary))
        else:
            _logger.info("Summary injected: False, summary_len=0")

        # Helper to update running summary (LLM-based with truncation fallback)
        def _update_running_summary(last_user_text: str, bot_text: str) -> None:
            max_chars = int(os.getenv("SPEAKING_SUMMARY_MAX_CHARS", "1200"))
            prev = getattr(self, "_running_summary", "")
            try:
                prompt = (
                    "Update the running summary of a tutoring session.\n"
                    "Keep key facts, goals, corrections, and user preferences. Be concise (<= 120 words).\n\n"
                    f"Current summary:\n{prev}\n\n"
                    "Last exchange:\n"
                    f"User: {last_user_text}\n"
                    f"Tutor: {bot_text}\n\n"
                    "Return only the updated summary."
                )
                messages = [
                    {"role": "system", "content": "You are a concise note taker for an English tutoring session."},
                    {"role": "user", "content": prompt},
                ]
                chunks = self.tutor_parent.openai_service.stream_chat_completion(
                    messages=messages, temperature=0.2, max_tokens=200
                )
                updated = "".join(chunks).strip()
                if updated:
                    self._running_summary = updated[:max_chars]
                    _logger.info("Running summary updated via LLM, new_len=%d", len(self._running_summary))
                    return
            except Exception as e:
                _logger.debug(f"LLM summary update failed, falling back to truncation: {e}")
            combined = (prev + " " + last_user_text + " " + bot_text).strip()
            self._running_summary = combined[-max_chars:]
            _logger.info("Running summary updated via truncation, new_len=%d", len(self._running_summary))

        # Helper to extract the latest user text (prefer text_for_llm)
        def _get_last_user_text() -> str:
            for m in reversed(current_history):
                if m.get("role") == "user":
                    return m.get("text_for_llm") or m.get("content") or ""
            return ""

        # Ensure variable is defined even if multimodal call raises repeatedly
        bot_text_response: str = ""

        try:
            # Retry policy: default to 1 attempt, configurable via env
            max_retries = int(os.getenv("AUDIO_RETRY_LIMIT", "1"))
            # Backoff base delay in milliseconds (0 = no backoff)
            base_delay_ms = int(os.getenv("AUDIO_RETRY_BACKOFF_MS", "0"))
            base_delay = max(0.0, base_delay_ms / 1000.0)
            attempts = 0
            audio_base64_data = None

            # Per-mode max_tokens configuration
            default_max_tokens = int(os.getenv("SPEAKING_MAX_TOKENS_DEFAULT", "700"))
            hybrid_max = int(os.getenv("SPEAKING_MAX_TOKENS_HYBRID", str(default_max_tokens)))
            immersive_max = int(os.getenv("SPEAKING_MAX_TOKENS_IMMERSIVE", str(default_max_tokens)))
            max_tokens = immersive_max if speaking_mode == "Immersive" else hybrid_max
            _logger.info(f"Using max_tokens={max_tokens} for mode={speaking_mode or 'hybrid'}")

            while attempts < max_retries and not audio_base64_data:
                try:
                    response = self.tutor_parent.openai_service.chat_multimodal(
                        messages=messages_for_llm, max_tokens=max_tokens
                    )
                    bot_text_response = extract_text_from_response(response)
                    _logger.info(f"LLM text length: {len(bot_text_response)} chars")
                    audio_base64_data = extract_audio_from_response(response)

                    if not audio_base64_data:
                        # Verifica se o erro é por limite de tokens
                        if "context_length_exceeded" in str(response).lower():
                            _logger.error("Erro: Limite de tokens excedido, não tentará novamente")
                            break

                        # Local diagnostics (in addition to utils.audio)
                        try:
                            resp_type = type(response).__name__
                            has_choices = hasattr(response, "choices") and bool(response.choices)
                            has_audio_attr = False
                            if has_choices:
                                msg = response.choices[0].message
                                has_audio_attr = hasattr(msg, "audio") and getattr(msg, "audio") is not None
                            _logger.info(
                                "Diag(no-audio): resp_type=%s has_choices=%s has_audio_attr=%s",
                                resp_type,
                                has_choices,
                                has_audio_attr,
                            )
                        except Exception as diag_e:
                            _logger.info("Diag(no-audio): failed to introspect response: %s", diag_e)

                        _logger.warning(f"No audio data in response (attempt {attempts+1}/{max_retries})")
                        # Backoff exponencial (condicional)
                        delay = base_delay * (2**attempts)
                        if delay > 0:
                            time.sleep(delay)
                except Exception as e:
                    _logger.error(
                        "Erro na tentativa %d: %s (%s)",
                        attempts + 1,
                        str(e),
                        type(e).__name__,
                    )
                    # If context length exceeded, do not keep retrying the same payload
                    if "context_length" in str(e).lower() or "maximum context length" in str(e).lower():
                        _logger.error("Context length exceeded. Will not retry further with same payload.")
                        break
                    delay = base_delay * (2**attempts)
                    if delay > 0:
                        time.sleep(delay)

                attempts += 1

            # If multimodal did not yield text at all, try text-only fallback
            if not bot_text_response:
                _logger.warning("Multimodal returned no text; attempting text-only fallback.")
                try:
                    # Use StreamingManager for robust text-only fallback with retries/backoff
                    sm = StreamingManager(
                        service=self.tutor_parent.openai_service,
                        telemetry=getattr(self.tutor_parent, "telemetry", None),
                    )
                    # Stream to UI incrementally using callbacks + queue
                    q: "queue.Queue" = queue.Queue()
                    acc: List[str] = []
                    done_flag = {"done": False}

                    def on_chunk(ch: str) -> None:
                        q.put(("data", ch))

                    def on_complete(txt: str) -> None:
                        q.put(("done", txt))

                    def on_error(e: Exception) -> None:
                        q.put(("error", e))

                    def worker() -> None:
                        try:
                            _ = sm.stream_text(
                                messages=messages_for_llm,
                                temperature=0.6,
                                max_tokens=max_tokens,
                                on_chunk=on_chunk,
                                on_complete=on_complete,
                                on_error=on_error,
                            )
                        except Exception as _:
                            # Error already reported via on_error
                            pass

                    t = threading.Thread(target=worker, daemon=True)
                    t.start()

                    # Prepare an empty assistant message to receive streamed chunks
                    current_history.append({"role": "assistant", "content": ""})

                    while True:
                        try:
                            kind, payload = q.get(timeout=0.1)
                        except queue.Empty:
                            # keep UI responsive while waiting
                            if done_flag["done"]:
                                break
                            # Yield current state even without new chunks to let UI refresh
                            yield current_history, current_history, None
                            continue

                        if kind == "data":
                            ch = payload
                            acc.append(ch)
                            current_history[-1]["content"] += ch
                            # Yield after each chunk
                            yield current_history, current_history, None
                        elif kind == "done":
                            done_flag["done"] = True
                            bot_text_response = payload or ""  # full text
                            break
                        elif kind == "error":
                            err = payload
                            _logger.error("Text-only streaming error: %s", err)
                            # Show partial text if any, then append error note
                            if acc:
                                yield current_history, current_history, None
                            current_history.append({"role": "assistant", "content": "(streaming error)"})
                            yield current_history, current_history, None
                            bot_text_response = "".join(acc)
                            break

                    # Ensure worker finished
                    t.join(timeout=0.1)
                    _logger.info("Text-only fallback produced %d chars.", len(bot_text_response))
                except Exception as e:
                    _logger.error("Text-only fallback failed: %s", e, exc_info=True)

            # --- Fallback to TTS if no audio is returned ---
            if bot_text_response and not audio_base64_data:
                _logger.warning("Multimodal response missing audio, falling back to TTS.")
                try:
                    # Generate audio from the text response (with safety cap)
                    tts_text = bot_text_response
                    max_tts_chars = int(os.getenv("TTS_MAX_CHARS", "1200"))
                    if len(tts_text) > max_tts_chars:
                        _logger.info(f"TTS input too long ({len(tts_text)} chars). Truncating to {max_tts_chars}.")
                        tts_text = tts_text[:max_tts_chars] + "..."
                    audio_bytes = self.tutor_parent.openai_service.text_to_speech(tts_text)
                    # The service returns raw bytes, so we need to encode it to base64
                    audio_base64_data = base64.b64encode(audio_bytes).decode("utf-8")
                    _logger.info("Successfully generated audio using TTS fallback.")
                except Exception as e:
                    _logger.error(f"TTS fallback failed: {e}", exc_info=True)
                    # If TTS also fails, we proceed with no audio
                    audio_base64_data = None

            # If we have text but no audio, send text-only fallback so the chat still updates
            if bot_text_response and not audio_base64_data:
                _logger.warning("Audio unavailable; sending text-only fallback message.")
                current_history.append({"role": "assistant", "content": bot_text_response})
                try:
                    _update_running_summary(_get_last_user_text(), bot_text_response)
                except Exception as e:
                    _logger.debug("Summary update skipped (text-only): %s", e)
                yield current_history, current_history, None
                return

            # If we don't have text either, surface an error message
            if not bot_text_response:
                _logger.error("Failed to get bot response text even after retries and TTS fallback.")
                error_msg = "I'm sorry, I couldn't generate a response."
                current_history.append({"role": "assistant", "content": error_msg})
                yield current_history, current_history, None
                return

            # --- Audio-First UX Implementation ---
            audio_bytes = base64.b64decode(audio_base64_data)
            # Respect configured output format for file suffix
            audio_fmt = os.getenv("AUDIO_OUTPUT_FORMAT", "wav").strip().lower() or "wav"
            suffix = f".{audio_fmt}" if not audio_fmt.startswith(".") else audio_fmt
            audio_path = save_audio_to_temp_file(audio_bytes, suffix=suffix)

            if speaking_mode == "Immersive":
                # In immersive mode, just add the audio player to the chat
                _logger.info("Immersive mode: Yielding audio for playback.")
                bot_message = {
                    "role": "assistant",
                    "content": (audio_path, None),
                    "text_for_llm": bot_text_response,
                }
                current_history.append(bot_message)
                try:
                    _update_running_summary(_get_last_user_text(), bot_text_response)
                except Exception as e:
                    _logger.debug("Summary update skipped (immersive): %s", e)
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

            # After finishing streaming, update the running summary
            try:
                _update_running_summary(_get_last_user_text(), bot_text_response)
            except Exception as e:
                _logger.debug("Summary update skipped (hybrid): %s", e)

        except Exception as e:
            _logger.error(f"Error calling chat_multimodal: {e}", exc_info=True)
            error_msg = f"Sorry, an error occurred while I was thinking. Please try again."

            current_history.append({"role": "assistant", "content": error_msg})

            yield current_history, current_history, None
