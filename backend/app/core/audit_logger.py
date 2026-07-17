"""Structured Security Audit Logging System for AgentShield.

Formats audit logs as structured JSON, outputs them to standard streams, and
automatically scrubs credentials, authorization headers, and session tokens.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any


class AuditLogger:
    """Structured JSON Security Audit Logger."""

    def __init__(self) -> None:
        self.sensitive_keys = {
            "password",
            "token",
            "cookie",
            "authorization",
            "secret",
            "key",
            "jwt",
            "access_token",
            "refresh_token",
            "passwd",
        }

    def _scrub(self, data: Any) -> Any:
        """Recursively scrub sensitive keys and token values from payloads."""
        if isinstance(data, dict):
            return {
                k: ("[REDACTED]" if any(sk in k.lower() for sk in self.sensitive_keys) else self._scrub(v))
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._scrub(item) for item in data]
        elif isinstance(data, str):
            lower_str = data.lower()
            if "bearer " in lower_str or "jwt" in lower_str:
                return "[REDACTED TOKEN]"
            return data
        return data

    def log_action(self, action: str, details: Any, operator: str) -> None:
        """Write a formatted audit log line to standard output."""
        scrubbed_details = self._scrub(details)
        log_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": "AUDIT",
            "action": action,
            "operator": operator,
            "details": scrubbed_details,
        }
        sys.stdout.write(json.dumps(log_payload) + "\n")
        sys.stdout.flush()

    def log_security_warning(self, event_type: str, details: Any) -> None:
        """Write a formatted security warning line to standard error."""
        scrubbed_details = self._scrub(details)
        log_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": "SECURITY_WARNING",
            "event_type": event_type,
            "details": scrubbed_details,
        }
        sys.stderr.write(json.dumps(log_payload) + "\n")
        sys.stderr.flush()


# Global audit logger singleton
audit_logger = AuditLogger()
