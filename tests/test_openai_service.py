import os
import sys
import types
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.openai_service import OpenAIService

class MockChunk:
    def __init__(self, content):
        delta = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(delta=delta)
        self.choices = [choice]


def test_stream_chat_completion_yields_tokens():
    service = OpenAIService(api_key="test")
    # Mock the streaming response from OpenAI
    generator = (MockChunk(part) for part in ["Hello", " world"])
    service.client.chat.completions.create = MagicMock(return_value=generator)

    chunks = list(service.stream_chat_completion(messages=[{"role": "user", "content": "Hi"}]))
    assert chunks == ["Hello", " world"]
