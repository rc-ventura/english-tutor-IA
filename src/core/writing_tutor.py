import logging
import threading
import queue
from typing import Any, Dict, Generator, List, Optional, Tuple
import gradio as gr
from src.core.base_tutor import BaseTutor
from src.utils.audio import save_audio_to_temp_file
from src.infra.streaming_manager import StreamingManager


class WritingTutor(BaseTutor):
    def _stream_response_to_history(
        self,
        messages: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Stream LLM response using StreamingManager and update history incrementally."""

        assistant_message = {"role": "assistant", "content": ""}
        history.append(assistant_message)

        # Emit initial state with empty assistant message
        yield history, history

        # Queue to receive streaming events from callbacks
        q: "queue.Queue" = queue.Queue()

        def on_chunk(ch: str) -> None:
            # Push chunk event for the generator loop to consume and yield
            q.put(("chunk", ch))

        def on_complete(full_text: str) -> None:
            q.put(("end", full_text))

        def on_error(err: Exception) -> None:
            q.put(("error", err))

        # Build a StreamingManager instance (reusing service and telemetry from parent)
        mgr = StreamingManager(service=self.openai_service, telemetry=getattr(self.tutor_parent, "telemetry", None))

        # Run the blocking stream_text in a background thread, feeding events to the queue
        def _runner():
            try:
                mgr.stream_text(messages=messages, on_chunk=on_chunk, on_complete=on_complete, on_error=on_error)
            except Exception as e:  # defensive, in case callbacks path didn't capture
                on_error(e)

        t = threading.Thread(target=_runner, daemon=True)
        t.start()

        reply_buffer = ""
        try:
            while True:
                kind, payload = q.get(timeout=60)  # generous timeout for long generations
                if kind == "chunk":
                    ch = payload
                    if ch:
                        reply_buffer += ch
                        assistant_message["content"] = reply_buffer
                        yield history, history
                elif kind == "end":
                    # Ensure content reflects final text (already accumulated)
                    assistant_message["content"] = reply_buffer or (payload or "").strip()
                    break
                elif kind == "error":
                    e = payload
                    logging.error(f"WritingTutor streaming error: {e}", exc_info=True)
                    assistant_message["content"] = f"Sorry, an error occurred: {e}"
                    yield history, history
                    break
        except queue.Empty:
            logging.warning("WritingTutor streaming timed out waiting for events.")
            assistant_message["content"] = reply_buffer or "Sorry, the response took too long. Please try again."
            yield history, history

    def process_input(
        self,
        input_data: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        writing_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Generator[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]], None, None]:
        """Evaluates an essay and streams the feedback into the chat history."""

        if not self.tutor_parent.openai_service:
            yield gr.Error("No valid OpenAI API key set. Please enter your API key in the settings."), []
            return

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

        if not self.tutor_parent.openai_service:
            error_message = {
                "role": "assistant",
                "content": "⚠️ No valid OpenAI API key set. Please enter your API key in the settings.",
            }
            current_history.append(error_message)
            yield current_history, current_history
            return

        user_request_message = f"Can you give me an essay topic for level {level} referring to {writing_type}."
        current_history.append({"role": "user", "content": user_request_message})

        yield current_history, current_history

        system_prompt = self.tutor_parent.get_system_message(mode="writing", level=level)
        prompt_for_llm = f"""Generate a topic for a writing essay for a student with level {level}. Also consider the writing type {writing_type}.

        Output Markdown with a COMPACT inline metadata header on the FIRST line (do not break items onto separate lines):
        - Use bold inline labels and separate items with " • " (middle dot). If the dot is not available, use " | ".
        - Include exactly these items, in this order: Essay Topic, Writing Type, Word Count.
        - Do NOT add blank lines between these items; keep them on one single line.
        - Immediately after this single-line header, insert a Markdown horizontal rule: --- on its own line.

        After the header, add one blank line, then provide:
        - Suggested Structure: a numbered list (1–3 concise items).
        - Additional Notes: 2–3 bullet points with simple language.

        Keep the language simple for beginner students. Emojis are optional; if used, keep them minimal.

        Example:

        Essay Topic: "My Favorite Animal" • Writing Type: Formal Essay • Word Count: 100–150
        ---

        Suggested Structure:
        1. Introduction — mention the animal.
        2. Body — describe appearance and behavior.
        3. Conclusion — explain why you like it.

        Additional Notes:
        - Use short sentences.
        - Use linking words like "and", "because".

        Respond ONLY in Markdown following this exact structure."""

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
