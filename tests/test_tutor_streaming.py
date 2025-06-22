from unittest.mock import MagicMock, patch
import base64

from src.core.speaking_tutor import SpeakingTutor, NO_AUDIO_UPDATE
from src.core.writing_tutor import WritingTutor


class DummyParent:
    def get_system_message(self, mode="writing", level=None):
        return "sys"


def test_writing_tutor_process_input_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Hello", " world"])
    with patch("src.core.writing_tutor.talker"):
        tutor = WritingTutor(service, DummyParent())
        history = []
        gen = tutor.process_input("My essay", history, level="B1")
        import copy

        first = copy.deepcopy(next(gen))
        second = copy.deepcopy(next(gen))
        last = None
        for item in gen:
            last = copy.deepcopy(item)
    # First yield shows the user's essay
    assert "Please evaluate this essay" in first[0][-1]["content"]
    # Second yield is the placeholder assistant message
    assert second[0][-1]["content"] == ""
    # Final output should contain the full response
    assert last[0][-1]["content"] == "Hello world"


def test_writing_tutor_generate_random_topic_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Topic", " suggestion"])
    with patch("src.core.writing_tutor.talker"):
        tutor = WritingTutor(service, DummyParent())
        history = []
        gen = tutor.generate_random_topic(level="B1", history=history)
        import copy

        first = copy.deepcopy(next(gen))
        second = copy.deepcopy(next(gen))
        last = None
        for item in gen:
            last = copy.deepcopy(item)
    assert first[0][-1]["content"].startswith("Can you give")
    assert second[0][-1]["content"] == ""
    assert last[0][-1]["content"] == "Topic suggestion"


def test_speaking_tutor_process_input_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Hi", " there"])
    mock_msg = MagicMock()
    mock_msg.content = "Hi there"
    mock_msg.audio = MagicMock()
    mock_msg.audio.data = base64.b64encode(b"audio").decode("utf-8")
    service.chat_multimodal.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])

    with patch("src.core.speaking_tutor.talker"):
        tutor = SpeakingTutor(service, DummyParent())
        history = [{"role": "user", "content": "Hello"}]
        gen = tutor.handle_bot_response_streaming(history=history, level="A1")
        import copy

        first = copy.deepcopy(next(gen))
        second = copy.deepcopy(next(gen))
        last = None
        for item in gen:
            last = copy.deepcopy(item)

    assert first[0][-1]["content"] == ""
    assert isinstance(first[2], str) and first[2].endswith(".wav")
    assert type(second[2]) is type(NO_AUDIO_UPDATE)
    assert second[0][-1]["content"] == "Hi"
    assert last[0][-1]["content"] == "Hi there"
