"""Utility helpers for the AgentShield Detection Engine.

This module provides three pure functions used by
:class:`~app.core.detector.DetectionEngine`:

* :func:`normalize_text` – canonicalises raw input before pattern matching.
* :func:`compile_rules` – pre-compiles a list of :class:`~app.core.models.ThreatRule`
  objects into ``(ThreatRule, re.Pattern)`` tuples for efficient repeated use.
* :func:`calculate_risk` – aggregates a list of
  :class:`~app.core.models.ThreatResult` objects into a single normalised risk
  score in ``[0.0, 1.0]``.

All functions are intentionally stateless so they can be unit-tested in
isolation and reused freely across different engine configurations.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

from app.core.models import ThreatResult, ThreatRule
from app.core.severity import Severity

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
CompiledRule = tuple[ThreatRule, re.Pattern[str]]
"""A pair of (rule definition, pre-compiled regex pattern)."""


def normalize_text(text: str) -> str:
    """Return a canonicalised version of *text* ready for pattern matching.

    The following transformations are applied in order:

    1. **Unicode normalisation** (NFC) – collapses composed/decomposed
       character variants to a single canonical form.
    2. **Lower-casing** – enables case-insensitive matching without requiring
       the ``re.IGNORECASE`` flag on every pattern.
    3. **Whitespace collapsing** – consecutive whitespace characters (spaces,
       tabs, newlines) are replaced by a single space so that patterns do not
       need to account for irregular spacing.
    4. **Strip** – leading and trailing whitespace is removed.

    Args:
        text: Raw input string from an agent message.

    Returns:
        Normalised string suitable for regex matching.

    Example::

        >>> normalize_text("  Ignore\\t\\tPrevious\\nInstructions  ")
        'ignore previous instructions'
    """
    # Step 1: Unicode normalisation
    normalised = unicodedata.normalize("NFC", text)
    # Step 2: Lower-case
    normalised = normalised.lower()
    # Step 3: Collapse whitespace
    normalised = re.sub(r"\s+", " ", normalised)
    # Step 4: Strip leading/trailing whitespace
    return normalised.strip()


def compile_rules(rules: Sequence[ThreatRule]) -> list[CompiledRule]:
    """Pre-compile a sequence of :class:`~app.core.models.ThreatRule` objects.

    Compiling each pattern once at startup (rather than per call) provides a
    significant throughput improvement when the engine inspects many messages.

    The ``re.IGNORECASE`` flag is applied globally as a defence-in-depth
    measure.  Note that :func:`normalize_text` already lower-cases text, but
    pre-normalised payloads passed directly to the engine will still be covered.

    Args:
        rules: An ordered sequence of :class:`~app.core.models.ThreatRule`
            instances to compile.

    Returns:
        A list of ``(ThreatRule, compiled_pattern)`` tuples in the same order
        as the input sequence.

    Raises:
        re.error: If any rule's ``pattern`` field contains an invalid regular
            expression.

    Example::

        compiled = compile_rules(DEFAULT_RULES)
        rule, pattern = compiled[0]
    """
    return [(rule, re.compile(rule.pattern, re.IGNORECASE)) for rule in rules]


def calculate_risk(threats: Sequence[ThreatResult]) -> float:
    """Compute a normalised aggregate risk score from a collection of threats.

    Algorithm
    ---------
    The score is computed using a *diminishing returns* formula so that many
    low-severity matches do not trivially produce a CRITICAL score:

    .. code-block:: text

        combined = 1 - ∏(1 - weight_i)  for each threat i

    This is equivalent to the probability that *at least one* independent event
    with probability ``weight_i`` occurs.  The result is inherently bounded in
    ``[0.0, 1.0]`` without an explicit ``min`` guard.

    Args:
        threats: A (possibly empty) sequence of
            :class:`~app.core.models.ThreatResult` objects produced by the
            engine.

    Returns:
        A float in ``[0.0, 1.0]``.  Returns ``0.0`` when *threats* is empty.

    Example::

        from app.core.severity import Severity
        score = calculate_risk(threats)
        assert 0.0 <= score <= 1.0
    """
    if not threats:
        return 0.0

    # Diminishing-returns aggregation: score = 1 - Π(1 - w_i)
    combined_non_risk: float = 1.0
    for threat in threats:
        weight = threat.rule.severity.weight
        combined_non_risk *= 1.0 - weight

    risk_score = 1.0 - combined_non_risk
    # Clamp to [0.0, 1.0] to guard against floating-point edge cases.
    return min(max(risk_score, 0.0), 1.0)
