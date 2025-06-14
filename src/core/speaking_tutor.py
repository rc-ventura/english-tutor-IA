import logging
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.core.base_tutor import BaseTutor
from src.utils.audio import talker


class SpeakingTutor(BaseTutor):
    def transcribe_audio_only(
        self, audio_file_path: Optional[str], history: List[Dict]
    ) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Transcribes the audio and appends user message to history."""
        if not audio_file_path:
            return (
                history + [{"role": "user", "content": "[No audio provided]"}],
                history,
            )

        try:
            transcription = self.openai_service.transcribe_audio(audio_file_path)
            if not transcription or not transcription.strip():
                transcription = "I couldn't understand the audio. Could you say it again?"
        except Exception as e:
            transcription = f"[Transcription error: {str(e)}]"

        history += [{"role": "user", "content": transcription}]
        return history, history

    def process_input(
        self, input_data: Any, history: List[Dict], level: Optional[str] = None
    ) -> Generator[Tuple[List[Dict], List[Dict]], None, None]:
        """Generate assistant response from latest history.

        The response is streamed token by token so that the frontend can update
        in real time. Each yielded value contains the current chat history to be
        displayed and the updated history state.
        """

        if not history or history[-1]["role"] != "user":
            yield history, history
            return

        system_prompt = self.tutor_parent.get_system_message(mode="speaking", level=level)
        messages = [{"role": "system", "content": system_prompt}] + history

        logging.info("Full prompt being sent to OpenAI:")
        logging.info({"system_prompt": system_prompt, "full_history": history})
        try:
            assistant_message = {"role": "assistant", "content": ""}
            history.append(assistant_message)
            for chunk in self.openai_service.stream_chat_completion(messages=messages):
                assistant_message["content"] += chunk
                yield history, history

        except Exception as e:
            logging.error(f"OpenAI chat completion error: {e}", exc_info=True)
            history[-1]["content"] = f"Sorry, I encountered an issue generating a response: {e}"
            yield history, history
            return

        reply = history[-1]["content"]

        try:
            talker(reply)
        except Exception as e:
            logging.warning(f"TTS error: {e}", exc_info=True)
            history[-1]["content"] += " (Note: audio playback failed)"

        yield history, history
