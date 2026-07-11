"""Replay Attack Protection Engine for AgentShield X.

Thread-safe sliding-window registry that tracks event IDs and payload signatures
to prevent replay and duplicate query attacks.
"""

from __future__ import annotations

import hashlib
import threading
import time


class ReplayProtector:
    """Thread-safe deduplication engine using a sliding window cache."""

    def __init__(self, window_seconds: float = 600.0) -> None:
        """Initialise the registry with a configured time window (default 10m)."""
        self.window_seconds = window_seconds
        self._registry: dict[str, float] = {}
        self._lock = threading.Lock()

    def check_and_register(self, event_id: str, agent_id: str, message: str, tool: str | None) -> bool:
        """Evaluate if the request contains a duplicate event ID or duplicate payload.

        Args:
            event_id: Unique transaction ID.
            agent_id: Requesting agent ID.
            message: Plain payload content.
            tool: Optional requested tool name.

        Returns:
            bool: True if the request is unique and successfully registered;
                  False if a replay signature was matched.
        """
        now = time.time()
        self.prune(now)

        # Build stable message content hash
        payload_raw = f"{agent_id}:{message}:{tool or ''}"
        payload_hash = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()

        with self._lock:
            # Check event ID and payload signature duplication
            if event_id in self._registry or payload_hash in self._registry:
                return False

            # Register signatures into window
            self._registry[event_id] = now
            self._registry[payload_hash] = now
            return True

    def prune(self, now: float) -> None:
        """Remove cache signatures older than the sliding window threshold."""
        with self._lock:
            cutoff = now - self.window_seconds
            expired = [k for k, ts in self._registry.items() if ts < cutoff]
            for k in expired:
                del self._registry[k]


# Singleton instance
replay_protector = ReplayProtector()
