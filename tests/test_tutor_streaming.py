from unittest.mock import MagicMock, patch

from src.core.speaking_tutor import SpeakingTutor
from src.core.writing_tutor import WritingTutor


class DummyParent:
    def get_system_message(self, mode="writing", level=None):
        return "sys"


def test_writing_tutor_process_input_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Hello", " world"])
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
    # Second yield contains the first streamed chunk
    assert second[0][-1]["content"] == ""
    # Final output should contain the full response
    assert last[0][-1]["content"] == "Hello world"


def test_writing_tutor_generate_random_topic_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Topic", " suggestion"])
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
    tutor = SpeakingTutor(service, DummyParent())
    history = [{"role": "user", "content": "Hello"}]

    with patch("src.core.speaking_tutor.extract_text_from_response", return_value="Hi there"), patch(
        "src.core.speaking_tutor.extract_audio_from_response", return_value=None
    ), patch("src.core.speaking_tutor.play_audio"):
        gen = tutor.process_input(None, history, level="A1")
        import copy

        result = copy.deepcopy(next(gen))

    assert result[0][-1]["content"] == "Hi there"
