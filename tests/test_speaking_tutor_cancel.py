import base64
import threading
from typing import Any

import pytest

from src.core.speaking_tutor import SpeakingTutor


class _Msg:
    def __init__(self, content: Any):
        self.content = content
        self.audio = None


class _Choice:
    def __init__(self, message):
        self.message = message


class _Resp:
    def __init__(self, message):
        self.choices = [_Choice(message)]


class FakeOpenAIService:
    def __init__(self, text: str, audio_bytes: bytes):
        self._text = text
        self._audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    def chat_multimodal(self, messages, max_tokens):
        # Return a response that has both text and audio content parts
        message = _Msg(
            [
                {"type": "output_text", "text": self._text},
                {"type": "output_audio", "audio": {"data": self._audio_b64}},
            ]
        )
        return _Resp(message)

    # Not used in this test but present in real service
    def stream_chat_completion(self, *args, **kwargs):
        raise NotImplementedError

    def text_to_speech(self, *args, **kwargs):
        return b"FAKE_TTS_AUDIO"


class FakeParent:
    def __init__(self, svc: FakeOpenAIService):
        self.openai_service = svc
        self.telemetry = None

    def get_system_message(self, mode: str, level: str | None = None) -> str:
        return "You are Sophia, a helpful tutor."


@pytest.mark.parametrize("speaking_mode", [None, "Hybrid"])  # validate default and explicit
def test_speaking_tutor_simulated_stream_can_be_cancelled(monkeypatch, speaking_mode):
    # Arrange: fake service with both audio and text so we go through audio-first + simulated text streaming path
    text = "This is a long response that will be streamed word by word for cancellation testing."
    svc = FakeOpenAIService(text=text, audio_bytes=b"WAVDATA")
    parent = FakeParent(svc)

    # SpeakingTutor expects BaseTutor init signature: (openai_service, tutor_parent)
    tutor = SpeakingTutor(openai_service=svc, tutor_parent=parent)

    history = [{"role": "user", "content": "Hello"}]

    # Speed up: avoid real sleep and audio duration
    monkeypatch.setattr("src.core.speaking_tutor.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.core.speaking_tutor.get_audio_duration", lambda _path: 0.0)

    stop_event = threading.Event()

    # Act: drive the generator
    gen = tutor.handle_bot_response(history=history, level="B1", speaking_mode=speaking_mode, stop_event=stop_event)

    # First yield should be audio playback (audio_path not None)
    chat_a, hist_a, audio_path = next(gen)
    assert audio_path is not None

    # Next, simulated text streaming starts; consume a couple of chunks then cancel
    partial_seen = False
    for _ in range(3):
        chat_b, hist_b, audio_b = next(gen)
        assert audio_b is None
        assert len(hist_b) >= 1
        last = hist_b[-1]
        if last.get("role") == "assistant" and isinstance(last.get("content"), str):
            if len(last["content"].strip()) > 0:
                partial_seen = True
                break

    assert partial_seen, "Expected some partial assistant text before cancelling."

    # Trigger cancellation
    stop_event.set()

    # Exhaust generator gracefully after cancellation (should stop soon)
    out_history = None
    for _ in range(50):
        try:
            chat_c, hist_c, audio_c = next(gen)
            out_history = hist_c
        except StopIteration:
            break

    assert out_history is not None, "Generator should have yielded state updates before stopping."
    last_msg = out_history[-1]
    assert last_msg["role"] == "assistant"
    # Ensure it didn't stream full text
    assert len(last_msg["content"].strip()) < len(text)
