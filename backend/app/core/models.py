"""Data models for the AgentShield Detection Engine.

This module provides three dataclasses that form the core data contract
between the detection components:

* :class:`ThreatRule`  – an immutable rule definition loaded from
  :mod:`app.core.rules`.
* :class:`ThreatResult` – a single match produced when a rule fires against
  inspected text.
* :class:`DetectionResult` – the final, aggregated report returned by
  :class:`~app.core.detector.DetectionEngine`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.severity import Severity


@dataclass(frozen=True)
class ThreatRule:
    """An immutable rule definition used by the detection engine.

    Attributes:
        pattern: A regular-expression string to match against normalised text.
        name: Short, human-readable rule identifier (e.g. ``"Command Injection"``).
        description: Longer explanation of what the rule detects and why it is
            dangerous.
        category: Broad threat category (e.g. ``"command_injection"``).
        severity: The :class:`~app.core.severity.Severity` level assigned to
            matches of this rule.

    Example::

        rule = ThreatRule(
            pattern=r"rm\s+-rf",
            name="Destructive Shell Command",
            description="Detects rm -rf which can wipe the filesystem.",
            category="command_injection",
            severity=Severity.CRITICAL,
        )
    """

    pattern: str
    name: str
    description: str
    category: str
    severity: Severity


@dataclass
class ThreatResult:
    """A single threat match produced by the detection engine.

    Attributes:
        rule: The :class:`ThreatRule` whose pattern was matched.
        matched_text: The exact substring that triggered the match.
        position: Zero-based character offset of the match start within the
            *normalised* text that was analysed.

    Example::

        result = ThreatResult(
            rule=some_rule,
            matched_text="rm -rf /",
            position=42,
        )
    """

    rule: ThreatRule
    matched_text: str
    position: int


@dataclass
class DetectionResult:
    """Aggregated output of a complete detection pass.

    Attributes:
        is_malicious: ``True`` when at least one threat was found.
        risk_score: Normalised aggregate risk in ``[0.0, 1.0]``.  Computed as a
            weighted combination of each matched rule's severity weight, capped
            at ``1.0``.
        threat_count: Total number of individual matches (one rule may match
            more than once).
        threats: All :class:`ThreatResult` objects, sorted by descending
            severity weight so the most dangerous findings appear first.

    Example::

        result = DetectionResult(
            is_malicious=True,
            risk_score=0.85,
            threat_count=3,
            threats=[...],
        )
    """

    is_malicious: bool
    risk_score: float
    threat_count: int
    threats: list[ThreatResult] = field(default_factory=list)
