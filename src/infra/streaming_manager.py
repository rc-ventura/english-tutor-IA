import os
import time
import logging
import threading
import queue
from typing import Any, Dict, List, Optional, Callable

from src.infra.telemetry import TelemetryService
from src.services.openai_service import OpenAIService

_logger = logging.getLogger(__name__)
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class StreamingManager:
    """Thin wrapper around OpenAIService.stream_chat_completion with retry/backoff and telemetry.

    Notes:
    - Heartbeats are emitted based on elapsed time while consuming chunks.
    - Active timeout (preempting a blocked iterator) is not enforced; we bound total time implicitly by retries.
    """

    def __init__(
        self,
        service: OpenAIService,
        telemetry: Optional[TelemetryService] = None,
        retry_limit: Optional[int] = None,
        backoff_ms: Optional[int] = None,
        heartbeat_ms: Optional[int] = None,
        timeout_ms: Optional[int] = None,
    ) -> None:
        self.service = service
        self.telemetry = telemetry
        self.retry_limit = int(os.getenv("STREAM_RETRY_LIMIT", str(retry_limit or 2)))
        self.backoff_ms = int(os.getenv("STREAM_RETRY_BACKOFF_MS", str(backoff_ms or 500)))
        self.heartbeat_ms = int(os.getenv("STREAM_HEARTBEAT_MS", str(heartbeat_ms or 1000)))
        self.timeout_ms = int(os.getenv("STREAM_TIMEOUT_MS", str(timeout_ms or 0)))

    def _consume_in_thread(self, iterator, out_queue: "queue.Queue", stop_event: threading.Event) -> None:
        try:
            for item in iterator:
                if stop_event.is_set():
                    break
                out_queue.put(("data", item))
            out_queue.put(("end", None))
        except Exception as e:
            out_queue.put(("error", e))

    def stream_text(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        if self.telemetry:
            self.telemetry.inc_counter(
                "stream_manager_started_total", {"model": getattr(self.service, "model", "unknown")}
            )

        attempts = 0
        last_err: Optional[Exception] = None
        backoff = max(0.0, self.backoff_ms / 1000.0)

        while attempts < max(1, self.retry_limit):
            attempts += 1
            if self.telemetry:
                self.telemetry.inc_counter("stream_manager_attempt_total", {"attempt": attempts})
            try:
                chunks = self.service.stream_chat_completion(
                    messages=messages, temperature=temperature, max_tokens=max_tokens
                )
                pieces: List[str] = []
                last_hb = time.perf_counter()
                cancelled = False

                if self.timeout_ms > 0:
                    inactivity = max(0.001, self.timeout_ms / 1000.0)
                    q: "queue.Queue" = queue.Queue()
                    local_stop = stop_event or threading.Event()
                    t = threading.Thread(target=self._consume_in_thread, args=(chunks, q, local_stop), daemon=True)
                    t.start()

                    while True:
                        # Cooperative cancellation
                        if stop_event is not None and stop_event.is_set():
                            cancelled = True
                            local_stop.set()
                            break
                        try:
                            kind, payload = q.get(timeout=inactivity)
                        except queue.Empty:
                            # inactivity timeout
                            if self.telemetry:
                                self.telemetry.log_event(
                                    "stream_manager_timeout",
                                    {"attempt": attempts, "received_chars": sum(len(p) for p in pieces)},
                                )
                            local_stop.set()
                            raise TimeoutError("Streaming inactivity timeout")

                        if kind == "data":
                            ch = payload
                            if ch:
                                pieces.append(ch)
                                if on_chunk:
                                    try:
                                        on_chunk(ch)
                                    except Exception as cb_e:  # pragma: no cover (defensive)
                                        _logger.debug("on_chunk callback raised: %s", cb_e)
                            now = time.perf_counter()
                            if (now - last_hb) * 1000.0 >= self.heartbeat_ms:
                                if self.telemetry:
                                    self.telemetry.log_event(
                                        "stream_manager_heartbeat",
                                        {"attempt": attempts, "received_chars": sum(len(p) for p in pieces)},
                                    )
                                last_hb = now
                        elif kind == "end":
                            break
                        elif kind == "error":
                            raise payload
                else:
                    for ch in chunks:
                        # Cooperative cancellation
                        if stop_event is not None and stop_event.is_set():
                            cancelled = True
                            break
                        if ch:
                            pieces.append(ch)
                            if on_chunk:
                                try:
                                    on_chunk(ch)
                                except Exception as cb_e:  # pragma: no cover (defensive)
                                    _logger.debug("on_chunk callback raised: %s", cb_e)
                        # heartbeat based on elapsed time
                        now = time.perf_counter()
                        if (now - last_hb) * 1000.0 >= self.heartbeat_ms:
                            if self.telemetry:
                                self.telemetry.log_event(
                                    "stream_manager_heartbeat",
                                    {"attempt": attempts, "received_chars": sum(len(p) for p in pieces)},
                                )
                            last_hb = now

                out = "".join(pieces).strip()
                if cancelled:
                    if self.telemetry:
                        self.telemetry.inc_counter("stream_manager_cancelled_total", {"attempt": attempts})
                    return out
                if out:
                    if self.telemetry:
                        self.telemetry.inc_counter("stream_manager_completed_total", {"attempts": attempts})
                    if on_complete:
                        try:
                            on_complete(out)
                        except Exception as cb_e:  # pragma: no cover (defensive)
                            _logger.debug("on_complete callback raised: %s", cb_e)
                    return out
                # If empty, consider retry (could be rate limited or filtered)
                _logger.info("Streaming produced empty output (attempt %d). Will retry if attempts remain.", attempts)
                if attempts < self.retry_limit and backoff > 0:
                    time.sleep(backoff * (2 ** (attempts - 1)))
                continue
            except Exception as e:
                last_err = e
                _logger.warning("Streaming attempt %d failed: %s", attempts, e)
                if self.telemetry:
                    self.telemetry.inc_counter(
                        "stream_manager_error_total", {"attempt": attempts, "error": type(e).__name__}
                    )
                if on_error:
                    try:
                        on_error(e)
                    except Exception as cb_e:  # pragma: no cover (defensive)
                        _logger.debug("on_error callback raised: %s", cb_e)
                if attempts < self.retry_limit and backoff > 0:
                    time.sleep(backoff * (2 ** (attempts - 1)))
                continue

        # All attempts exhausted
        if last_err is not None:
            raise last_err
        # Return empty if we never got content nor exceptions (edge case)
        return ""
