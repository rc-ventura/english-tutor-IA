import time
from typing import Any, Dict, Generator, List, Optional

import pytest

from src.infra.streaming_manager import StreamingManager


class StubTelemetry:
    def __init__(self) -> None:
        self.counters: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.hists: List[Dict[str, Any]] = []

    def inc_counter(self, name: str, labels: Optional[Dict[str, Any]] = None) -> None:
        self.counters.append({"name": name, "labels": labels or {}})

    def observe_hist(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None) -> None:
        self.hists.append({"name": name, "value": value, "labels": labels or {}})

    def log_event(self, name: str, labels: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({"name": name, "labels": labels or {}})


def test_stream_success_single_attempt(monkeypatch):
    class ServiceOK:
        model = "gpt-4o-mini"

        def stream_chat_completion(
            self, messages: List[Dict[str, Any]], temperature: float, max_tokens: int
        ) -> Generator[str, None, None]:
            yield "Hello "
            yield "world"

    tel = StubTelemetry()
    sm = StreamingManager(service=ServiceOK(), telemetry=tel, retry_limit=1, backoff_ms=0)
    out = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    assert out == "Hello world"
    # Started and completed counters present
    names = [c["name"] for c in tel.counters]
    assert "stream_manager_started_total" in names
    assert "stream_manager_completed_total" in names


def test_stream_retry_after_empty_output():
    class ServiceEmptyThenOK:
        def __init__(self) -> None:
            self.calls = 0

        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            self.calls += 1

            # Return a generator. First attempt yields nothing; second yields tokens.
            def gen():
                if self.calls == 1:
                    if False:
                        yield ""  # pragma: no cover (keep generator type)
                    return
                yield "A"
                yield "B"
                yield "C"

            return gen()

    tel = StubTelemetry()
    sm = StreamingManager(service=ServiceEmptyThenOK(), telemetry=tel, retry_limit=2, backoff_ms=0)
    out = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    assert out == "ABC"
    # Ensure we attempted twice
    attempts = [c for c in tel.counters if c["name"] == "stream_manager_attempt_total"]
    assert len(attempts) == 2


def test_stream_retry_after_exception_then_success():
    class ServiceFailThenOK:
        def __init__(self) -> None:
            self.calls = 0

        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary")
            return iter(["ok"])  # second attempt succeeds

    tel = StubTelemetry()
    sm = StreamingManager(service=ServiceFailThenOK(), telemetry=tel, retry_limit=2, backoff_ms=0)
    out = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    assert out == "ok"
    errors = [c for c in tel.counters if c["name"] == "stream_manager_error_total"]
    assert len(errors) == 1


def test_stream_exhausts_and_raises():
    class ServiceAlwaysFail:
        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            raise ConnectionError("boom")

    tel = StubTelemetry()
    sm = StreamingManager(service=ServiceAlwaysFail(), telemetry=tel, retry_limit=2, backoff_ms=0)
    with pytest.raises(ConnectionError):
        _ = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)


def test_heartbeat_emitted():
    class ServiceSlowChunks:
        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            # Simulate delays between chunks so StreamingManager can emit heartbeats
            def gen():
                yield "x"
                time.sleep(0.02)
                yield "y"
                time.sleep(0.02)
                yield "z"

            return gen()

    tel = StubTelemetry()
    sm = StreamingManager(service=ServiceSlowChunks(), telemetry=tel, retry_limit=1, backoff_ms=0, heartbeat_ms=5)
    out = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    assert out == "xyz"
    hb = [e for e in tel.events if e["name"] == "stream_manager_heartbeat"]
    assert len(hb) >= 1


def test_stream_timeout_then_retry_success():
    class ServiceTimeoutThenOK:
        def __init__(self) -> None:
            self.calls = 0

        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            self.calls += 1

            if self.calls == 1:
                # First attempt: emit one token then stall beyond timeout
                def gen():
                    yield "x"
                    time.sleep(0.05)  # 50ms
                    yield "y"

                return gen()

            # Second attempt: quick success
            return iter(["ok"])

    tel = StubTelemetry()
    sm = StreamingManager(
        service=ServiceTimeoutThenOK(), telemetry=tel, retry_limit=2, backoff_ms=0, heartbeat_ms=5, timeout_ms=10
    )
    out = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    assert out == "ok"
    # We should have recorded at least one timeout event and one error counter
    timeout_events = [e for e in tel.events if e["name"] == "stream_manager_timeout"]
    assert len(timeout_events) >= 1
    errors = [c for c in tel.counters if c["name"] == "stream_manager_error_total"]
    assert len(errors) >= 1


def test_stream_timeout_exhausts_and_raises():
    class ServiceAlwaysTimeout:
        model = "gpt-4o-mini"

        def stream_chat_completion(self, messages, temperature, max_tokens):
            # Always stall beyond timeout
            def gen():
                yield "a"
                time.sleep(0.05)
                yield "b"

            return gen()

    tel = StubTelemetry()
    sm = StreamingManager(
        service=ServiceAlwaysTimeout(), telemetry=tel, retry_limit=1, backoff_ms=0, heartbeat_ms=5, timeout_ms=10
    )
    with pytest.raises(TimeoutError):
        _ = sm.stream_text(messages=[{"role": "user", "content": "hi"}], temperature=0.6, max_tokens=32)
    timeout_events = [e for e in tel.events if e["name"] == "stream_manager_timeout"]
    assert len(timeout_events) >= 1
