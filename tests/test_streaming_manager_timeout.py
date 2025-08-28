import time
import pytest

from src.infra.streaming_manager import StreamingManager


class FakeBlockingService:
    """Service whose stream blocks longer than timeout before yielding."""

    def stream_chat_completion(self, *args, **kwargs):
        def gen():
            # Block for 200ms before yielding anything
            time.sleep(0.2)
            yield "hello"

        return gen()


def test_streaming_manager_inactivity_timeout(monkeypatch):
    # Configure tight timeout and single attempt to surface the error immediately
    monkeypatch.setenv("STREAM_TIMEOUT_MS", "50")
    monkeypatch.setenv("STREAM_RETRY_LIMIT", "1")
    monkeypatch.setenv("STREAM_HEARTBEAT_MS", "1")

    mgr = StreamingManager(service=FakeBlockingService(), telemetry=None)

    with pytest.raises(TimeoutError):
        _ = mgr.stream_text(
            [
                {"role": "user", "content": "Hi"},
            ]
        )
