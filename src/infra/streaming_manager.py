import os
import time
import logging
from typing import Any, Dict, List, Optional

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
    ) -> None:
        self.service = service
        self.telemetry = telemetry
        self.retry_limit = int(os.getenv("STREAM_RETRY_LIMIT", str(retry_limit or 2)))
        self.backoff_ms = int(os.getenv("STREAM_RETRY_BACKOFF_MS", str(backoff_ms or 500)))
        self.heartbeat_ms = int(os.getenv("STREAM_HEARTBEAT_MS", str(heartbeat_ms or 1000)))

    def stream_text(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
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
                for ch in chunks:
                    if ch:
                        pieces.append(ch)
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
                if out:
                    if self.telemetry:
                        self.telemetry.inc_counter("stream_manager_completed_total", {"attempts": attempts})
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
                if attempts < self.retry_limit and backoff > 0:
                    time.sleep(backoff * (2 ** (attempts - 1)))
                continue

        # All attempts exhausted
        if last_err is not None:
            raise last_err
        # Return empty if we never got content nor exceptions (edge case)
        return ""
