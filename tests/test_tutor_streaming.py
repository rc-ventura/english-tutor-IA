import types
from unittest.mock import MagicMock, patch
from src.core.writing_tutor import WritingTutor

class DummyParent:
    def get_system_message(self, mode='writing', level=None):
        return 'sys'

def test_writing_tutor_process_input_streams():
    service = MagicMock()
    service.stream_chat_completion.return_value = iter(["Hello", " world"])
    with patch("src.core.writing_tutor.talker"):
        tutor = WritingTutor(service, DummyParent())
        history = []
        gen = tutor.process_input("My essay", history, level="B1")
        outputs = list(gen)
    assert outputs[0][0][-1]["content"] == "Hello"
    assert outputs[-1][0][-1]["content"] == "Hello world"
