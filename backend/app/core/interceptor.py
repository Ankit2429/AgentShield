"""Message Interceptor for AgentShield X.

Protects against:
- Indirect Prompt Injection
- Recursive Tool Loops
- Cross-Agent Contamination
- Data Exfiltration
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any

logger = logging.getLogger("agentshield.interceptor")


class MessageInterceptor:
    """Interceptors to scan and validate message telemetry before model evaluation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Track nested tool execution counts per session to prevent Recursive Tool Loops
        self._session_tool_chains: dict[str, list[str]] = {}

        # Data Exfiltration regex patterns (Private Keys, API Keys, Passwords, Credit Cards)
        self._exfil_patterns = [
            (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"), "Private Cryptographic Key"),
            (re.compile(r"\b[A-Za-z0-9+/]{40}\b"), "Potential Cloud API Secret/Token"),
            (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "Potential Payment Card Number"),
            (
                re.compile(
                    r"(?:password|passwd|secret|apikey|credential)\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*()_+]{8,}['\"]"
                ),
                "Plaintext Password/API Key Assignment",
            ),
        ]

        # Indirect Prompt Injection patterns (XML tag overrides, Markdown instruction injection)
        self._injection_patterns = [
            (
                re.compile(r"<instructions?>.*?</instructions?>", re.IGNORECASE | re.DOTALL),
                "XML Tag Instruction Override",
            ),
            (re.compile(r"\[//\]:\s*#\s*\(.*?\)", re.IGNORECASE), "Markdown Comment Instruction Injection"),
            (re.compile(r"(?:system\s+override|override\s+system\s+instructions?)", re.IGNORECASE), "Instruction Override Phrase"),
        ]

    def intercept_message(
        self,
        message: str,
        session_id: str | None = None,
        agent_id: str | None = None,
        requested_tool: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Inspect the message content and log context for security anomalies.

        Returns:
            dict: Evaluation result with boolean flag 'allow' and anomaly details.
        """
        findings = []

        # 1. Check for Indirect Prompt Injection
        for pattern, label in self._injection_patterns:
            if pattern.search(message):
                findings.append(f"Indirect Prompt Injection detected: {label}")

        # 2. Check for Data Exfiltration
        for pattern, label in self._exfil_patterns:
            if pattern.search(message):
                findings.append(f"Data Exfiltration attempt blocked: {label}")

        # 3. Check for Recursive Tool Loops
        if session_id and requested_tool:
            with self._lock:
                chain = self._session_tool_chains.setdefault(session_id, [])
                chain.append(requested_tool)

                # Check for recursive looping (e.g. same tool called > 3 times consecutively)
                consecutive_count = 1
                for i in range(len(chain) - 2, -1, -1):
                    if chain[i] == requested_tool:
                        consecutive_count += 1
                    else:
                        break

                if consecutive_count > 3:
                    findings.append(
                        f"Recursive Tool Loop detected: consecutive calls to {requested_tool!r} ({consecutive_count} times)"
                    )
                elif len(chain) > 8:
                    findings.append(
                        f"Recursive Tool Loop detected: tool invocation chain exceeded limit ({len(chain)} total calls)"
                    )

        # 4. Check for Cross-Agent Contamination
        if context and agent_id:
            context_agent = context.get("owner_agent_id")
            if context_agent and context_agent != agent_id:
                findings.append(
                    f"Cross-Agent Contamination warning: agent {agent_id!r} "
                    f"attempted to read context owned by {context_agent!r}"
                )

        allow = len(findings) == 0
        return {
            "allow": allow,
            "findings": findings,
            "message": message,
        }

    def clear_session(self, session_id: str) -> None:
        """Prune tool chain context when session completes to prevent memory leaks."""
        with self._lock:
            self._session_tool_chains.pop(session_id, None)


# Global singleton instance
message_interceptor = MessageInterceptor()
