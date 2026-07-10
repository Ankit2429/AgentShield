"""Trust Intelligence Engine for AgentShield.

This module is the authoritative long-term reputation layer for every AI agent
interacting with the AgentShield platform.  It is deliberately architected as
a **clean, extensible MVP**: the surface area is small and every responsibility
is isolated in its own helper, making future capabilities (listed below) safe
to bolt on without touching existing logic.

Architecture overview
---------------------
::

    ┌──────────────────────────────────────────────────────────┐
    │                       TrustEngine                        │
    │                                                          │
    │  register_agent()  ──► _create_profile()                 │
    │  record_success()  ─┐                                    │
    │  record_suspicious()├──► _increment_counter()            │
    │  record_block()    ─┘     update_scores()                │
    │                            ├─ _compute_behavior_score()  │
    │                            ├─ _compute_policy_score()    │
    │                            └─ _composite_trust_score()  ◄── swap here │
    │  calculate_grade()  ──► _GRADE_THRESHOLDS               │
    │  calculate_status() ──► _STATUS_THRESHOLDS              │
    │  calculate_trend()  ──► _score_history ring-buffer      │
    └──────────────────────────────────────────────────────────┘

Future extension points (marked with TODO comments throughout the file):
- ``[STORAGE]``        Persistent storage (replace _store_* helpers).
- ``[REPLAY]``         Replay-attack protection per agent.
- ``[IDENTITY]``       Cryptographic identity verification.
- ``[SYBIL]``          Sybil-attack resistance (cross-agent correlation).
- ``[DECAY]``          Time-based score decay for inactive agents.
- ``[AUDIT]``          Structured audit-log emission per event.
- ``[FINGERPRINT]``    Behavioural fingerprinting / anomaly detection.

Typical usage::

    engine = TrustEngine()

    engine.register_agent("agent-1")          # explicit registration
    engine.record_success("agent-2")           # auto-registers on first contact
    engine.record_suspicious("agent-2")
    engine.record_block("agent-2")

    profile = engine.get_profile("agent-2")
    print(profile.trust_score, profile.status, profile.security_grade, profile.trend)

    print(engine.all_profiles())
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ============================================================================
# Enumerations
# ============================================================================


class TrustStatus(str, Enum):
    """Operational status of an AI agent derived from its trust score.

    Statuses form an ordered lifecycle from a brand-new agent through to one
    that has been permanently blocked.  The mapping from score → status is
    owned by :meth:`TrustEngine.calculate_status`.

    Attributes:
        NEW: Agent has just been registered; no interactions recorded yet.
        VERIFIED: Score ≥ 0.80 — agent has demonstrated consistent behaviour.
        TRUSTED: Score ≥ 0.90 — highly reliable, minimal policy violations.
        MONITOR: Score ≥ 0.55 — marginal agent requiring active observation.
        SUSPICIOUS: Score ≥ 0.30 — multiple policy violations detected.
        QUARANTINED: Score ≥ 0.10 — high-risk; interactions severely restricted.
        BLOCKED: Score < 0.10 — denied all further interaction.
    """

    NEW = "NEW"
    TRUSTED = "TRUSTED"
    VERIFIED = "VERIFIED"
    MONITOR = "MONITOR"
    SUSPICIOUS = "SUSPICIOUS"
    QUARANTINED = "QUARANTINED"
    BLOCKED = "BLOCKED"


class TrustTrend(str, Enum):
    """Direction of an agent's trust score over recent interactions.

    Attributes:
        IMPROVING: Score has risen above the stability threshold recently.
        STABLE: Score has remained roughly constant.
        DECLINING: Score has fallen below the stability threshold recently.
    """

    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


# ============================================================================
# Tunable constants — change here, not inside methods
# ============================================================================

# Starting score for every newly registered agent.
_INITIAL_TRUST_SCORE: float = 0.85

# Sub-score starting values (neutral priors).
_INITIAL_BEHAVIOR_SCORE: float = 1.0
_INITIAL_POLICY_SCORE: float = 1.0

# ── Composite score weights ──────────────────────────────────────────────────
# These three values must sum to 1.0.
# To change the weighting model, modify ONLY _composite_trust_score().
_WEIGHT_HISTORY: float = 0.40   # Inertia: the previous trust score.
_WEIGHT_BEHAVIOR: float = 0.35  # Reward signal: how often the agent succeeds.
_WEIGHT_POLICY: float = 0.25    # Penalty signal: how compliant the agent is.

# ── Sub-score computation ────────────────────────────────────────────────────
# Minimum request count before success_rate is used at full weight.
_BEHAVIOR_COLD_START_THRESHOLD: int = 5
# Multiplier that amplifies the violation-rate penalty in policy_score.
_POLICY_VIOLATION_MULTIPLIER: float = 1.5

# ── Trend detection ──────────────────────────────────────────────────────────
# Number of consecutive score snapshots to keep for trend analysis.
_TREND_WINDOW: int = 10
# Minimum absolute score change to classify a trend as non-stable.
_TREND_STABILITY_THRESHOLD: float = 0.04

# ── Status thresholds (descending; first match wins) ────────────────────────
_STATUS_THRESHOLDS: list[tuple[float, TrustStatus]] = [
    (0.90, TrustStatus.TRUSTED),
    (0.80, TrustStatus.VERIFIED),
    (0.55, TrustStatus.MONITOR),
    (0.30, TrustStatus.SUSPICIOUS),
    (0.10, TrustStatus.QUARANTINED),
    (0.00, TrustStatus.BLOCKED),
]

# ── Security grade thresholds (descending; first match wins) ─────────────────
_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (0.95, "A+"),
    (0.85, "A"),
    (0.75, "B"),
    (0.60, "C"),
    (0.40, "D"),
    (0.00, "F"),
]


# ============================================================================
# Data model
# ============================================================================


@dataclass
class AgentTrustProfile:
    """Complete, long-term trust profile for a single AI agent.

    Every field is either a direct observable (counters, timestamps) or a
    derived metric maintained by :class:`TrustEngine`.  The ``future_metadata``
    dict is the designated extension point for any context that does not yet
    have a typed field.

    Attributes:
        agent_id: Unique, stable identifier for this agent (string / UUID).
        trust_score: Composite trust score in ``[0.0, 1.0]``.  This is the
            primary signal consumed by downstream policy engines.
        behavior_score: Behavioural sub-score (``[0.0, 1.0]``) derived from
            the agent's success rate.  A *real input* to ``trust_score``.
        policy_score: Policy-compliance sub-score (``[0.0, 1.0]``) penalised
            by blocked and suspicious events.  A *real input* to ``trust_score``.
        security_grade: Human-readable grade derived from ``trust_score``
            (``"A+"``, ``"A"``, ``"B"``, ``"C"``, ``"D"``, or ``"F"``).
        status: Current :class:`TrustStatus` lifecycle state.
        trend: Recent :class:`TrustTrend` computed over the score history
            window.
        successful_requests: Cumulative count of clean interactions.
        blocked_requests: Cumulative count of blocked (malicious) interactions.
        suspicious_requests: Cumulative count of flagged-but-allowed
            interactions.
        created_at: UTC timestamp when this profile was first created.
        last_updated: UTC timestamp of the most recent score update.
        future_metadata: Open-ended dict for extension data (e.g. fingerprints,
            geographic hints, model version tags).  Consumers should namespace
            keys to avoid collisions (e.g. ``"fingerprint.hash"``).
        _score_history: Internal ring-buffer of recent ``trust_score``
            snapshots used for trend computation.  Not part of the public API.

    Example::

        profile = AgentTrustProfile(agent_id="agent-7")
        print(profile.trust_score)    # 0.85
        print(profile.status)         # TrustStatus.NEW
        print(profile.security_grade) # "A"
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    agent_id: str

    # ── Composite score ───────────────────────────────────────────────────────
    trust_score: float = _INITIAL_TRUST_SCORE

    # ── Sub-scores (real inputs to trust_score, not decorative) ──────────────
    behavior_score: float = _INITIAL_BEHAVIOR_SCORE
    policy_score: float = _INITIAL_POLICY_SCORE

    # ── Derived metadata ──────────────────────────────────────────────────────
    security_grade: str = "A"
    status: TrustStatus = TrustStatus.NEW
    trend: TrustTrend = TrustTrend.STABLE

    # ── Interaction counters ──────────────────────────────────────────────────
    successful_requests: int = 0
    blocked_requests: int = 0
    suspicious_requests: int = 0

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ── Extension point ───────────────────────────────────────────────────────
    future_metadata: dict[str, Any] = field(default_factory=dict)

    # ── Internal: score history ring-buffer (not serialised by default) ───────
    _score_history: list[float] = field(default_factory=list, repr=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Computed properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def total_requests(self) -> int:
        """Total interaction events recorded for this agent.

        Returns:
            int: ``successful_requests + blocked_requests + suspicious_requests``.
        """
        return self.successful_requests + self.blocked_requests + self.suspicious_requests

    @property
    def success_rate(self) -> float:
        """Ratio of successful requests to total requests.

        Returns:
            float: Value in ``[0.0, 1.0]``.  Returns ``1.0`` before any
            interactions have been recorded (neutral prior).
        """
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def violation_rate(self) -> float:
        """Ratio of policy violations (blocked + suspicious) to total requests.

        Returns:
            float: Value in ``[0.0, 1.0]``.  Returns ``0.0`` before any
            interactions have been recorded.
        """
        if self.total_requests == 0:
            return 0.0
        return (self.blocked_requests + self.suspicious_requests) / self.total_requests


# ============================================================================
# Trust Engine
# ============================================================================


class TrustEngine:
    """Long-term trust reputation engine for AI agents.

    Maintains an :class:`AgentTrustProfile` for every agent it has observed.
    Unknown agents are auto-registered on first contact.

    Responsibilities
    ----------------
    * Register and persist agent profiles.
    * Accept raw interaction events (success / suspicious / block).
    * Derive ``behavior_score``, ``policy_score``, and composite ``trust_score``.
    * Map scores to a human-readable ``security_grade`` and lifecycle ``status``.
    * Track directional ``trend`` over a sliding history window.

    Thread safety
    -------------
    A :class:`threading.RLock` serialises all profile reads and writes, making
    the engine safe for concurrent use across FastAPI request-handler threads.

    Singleton pattern
    -----------------
    The engine is designed to be instantiated **once** at application startup
    (e.g. in ``main.py`` or a dependency-injection container) and shared across
    all request handlers.  It is not itself a singleton; the caller decides the
    lifecycle.

    Database migration
    ------------------
    All storage access is routed through three private helpers:

    * :meth:`_store_profile`  — upsert a profile.
    * :meth:`_fetch_profile`  — read a profile by agent_id.
    * :meth:`_fetch_all`      — iterate over every stored profile.

    Replace the bodies of those three methods to migrate to SQLAlchemy, Redis,
    or any other persistence backend without touching business logic.

    Example::

        engine = TrustEngine()
        engine.register_agent("agent-1")
        engine.record_success("agent-1")
        profile = engine.get_profile("agent-1")
        print(profile.security_grade, profile.status, profile.trend)
    """

    def __init__(self) -> None:
        """Initialise the engine with an empty in-memory profile store."""
        # TODO [STORAGE]: Replace with a database session / connection pool.
        self._profiles: dict[str, AgentTrustProfile] = {}
        self._lock: threading.RLock = threading.RLock()

    # =========================================================================
    # Public API — Registration & Retrieval
    # =========================================================================

    def register_agent(self, agent_id: str) -> AgentTrustProfile:
        """Explicitly register a new agent and return its initial profile.

        If the agent is already registered the existing profile is returned
        unchanged.  This method is idempotent.

        Args:
            agent_id: Unique, stable identifier for the agent.  Must be a
                non-empty string.

        Returns:
            The (possibly existing) :class:`AgentTrustProfile` for *agent_id*.

        Raises:
            ValueError: If *agent_id* is empty or not a string.

        Example::

            profile = engine.register_agent("agent-99")
            assert profile.status == TrustStatus.NEW
        """
        _validate_agent_id(agent_id)
        with self._lock:
            return self._get_or_create(agent_id)

    def get_profile(self, agent_id: str) -> Optional[AgentTrustProfile]:
        """Return the trust profile for *agent_id*, or ``None`` if unknown.

        This is a **read-only** operation.  The profile is not modified.

        Args:
            agent_id: Agent identifier to look up.

        Returns:
            :class:`AgentTrustProfile` if found, ``None`` otherwise.

        Example::

            profile = engine.get_profile("agent-42")
            if profile is None:
                print("Agent has never been seen.")
        """
        _validate_agent_id(agent_id)
        with self._lock:
            return self._fetch_profile(agent_id)

    def all_profiles(self) -> list[AgentTrustProfile]:
        """Return a snapshot of all tracked agent profiles.

        The returned list is a copy of the current state; mutations do not
        affect the engine's internal storage.

        Returns:
            list[AgentTrustProfile]: All profiles, in unspecified order.
        """
        with self._lock:
            return list(self._fetch_all())

    # =========================================================================
    # Public API — Event Recording
    # =========================================================================

    def record_success(self, agent_id: str) -> AgentTrustProfile:
        """Record a successful (clean) interaction for *agent_id*.

        A successful interaction is one where the agent's request completed
        without triggering any security policy.  It applies a small positive
        reinforcement to the agent's scores.

        Auto-registers the agent if it has not been seen before.

        Args:
            agent_id: Agent identifier.

        Returns:
            Updated :class:`AgentTrustProfile`.

        Example::

            profile = engine.record_success("agent-1")
            assert profile.successful_requests == 1
        """
        return self._record_event(agent_id, "success")

    def record_suspicious(self, agent_id: str) -> AgentTrustProfile:
        """Record a suspicious (policy-warning) interaction for *agent_id*.

        A suspicious event is one where the agent's request raised a policy
        flag but was ultimately allowed through (e.g. a low-confidence
        detection).  It applies a moderate penalty to the agent's scores.

        Auto-registers the agent if it has not been seen before.

        Args:
            agent_id: Agent identifier.

        Returns:
            Updated :class:`AgentTrustProfile`.
        """
        return self._record_event(agent_id, "suspicious")

    def record_block(self, agent_id: str) -> AgentTrustProfile:
        """Record a blocked (malicious) interaction for *agent_id*.

        A block event means the agent's request was detected as a threat and
        denied.  It applies a significant penalty to the agent's scores.

        Auto-registers the agent if it has not been seen before.

        Args:
            agent_id: Agent identifier.

        Returns:
            Updated :class:`AgentTrustProfile`.
        """
        return self._record_event(agent_id, "block")

    # =========================================================================
    # Public API — Score & Metadata Computation
    # =========================================================================

    def update_scores(self, profile: AgentTrustProfile) -> None:
        """Recompute all derived scores and metadata for *profile* in-place.

        This is the **central update pipeline**.  Call order matters:

        1. Recompute ``behavior_score`` from interaction counters.
        2. Recompute ``policy_score`` from violation counters.
        3. Recompute composite ``trust_score`` from the three inputs above.
        4. Recompute ``security_grade``, ``status``, and ``trend``.
        5. Stamp ``last_updated``.

        The composite score formula is intentionally isolated inside
        :meth:`_composite_trust_score` so the weighting model can be replaced
        without touching this orchestration method.

        Args:
            profile: The :class:`AgentTrustProfile` to update in-place.
        """
        # Sub-scores first — they are inputs to the composite.
        profile.behavior_score = self._compute_behavior_score(profile)
        profile.policy_score = self._compute_policy_score(profile)

        # Composite trust score: the only place history/behavior/policy are combined.
        profile.trust_score = self._composite_trust_score(
            history_score=profile.trust_score,
            behavior_score=profile.behavior_score,
            policy_score=profile.policy_score,
        )

        # Push the new score into the trend ring-buffer.
        self._push_score_history(profile)

        # Derived metadata.
        profile.security_grade = self.calculate_grade(profile.trust_score)
        profile.status = self.calculate_status(profile)
        profile.trend = self.calculate_trend(profile)

        # Timestamp.
        profile.last_updated = datetime.now(timezone.utc)

        # TODO [AUDIT]: Emit a structured audit-log entry here with the full
        #               before/after state and the event that triggered this update.

    def calculate_grade(self, trust_score: float) -> str:
        """Map a numeric trust score to a security grade string.

        Args:
            trust_score: A float in ``[0.0, 1.0]``.

        Returns:
            str: One of ``"A+"``, ``"A"``, ``"B"``, ``"C"``, ``"D"``, ``"F"``.

        Example::

            assert engine.calculate_grade(0.96) == "A+"
            assert engine.calculate_grade(0.40) == "D"
            assert engine.calculate_grade(0.10) == "F"
        """
        for threshold, grade in _GRADE_THRESHOLDS:
            if trust_score >= threshold:
                return grade
        return "F"

    def calculate_status(self, profile: AgentTrustProfile) -> TrustStatus:
        """Determine the lifecycle status of *profile* from its trust score.

        An agent retains ``TrustStatus.NEW`` until it records at least one
        interaction, after which the score-based threshold table takes over.

        Args:
            profile: Source profile.

        Returns:
            :class:`TrustStatus` corresponding to the agent's current score
            and interaction history.
        """
        if profile.total_requests == 0:
            return TrustStatus.NEW

        for threshold, status in _STATUS_THRESHOLDS:
            if profile.trust_score >= threshold:
                return status

        return TrustStatus.BLOCKED

    def calculate_trend(self, profile: AgentTrustProfile) -> TrustTrend:
        """Determine the recent score trend from the profile's history buffer.

        Uses the delta between the oldest and newest score in the ring-buffer.
        Returns :attr:`TrustTrend.STABLE` when fewer than two snapshots exist.

        Args:
            profile: Source profile containing ``_score_history``.

        Returns:
            :class:`TrustTrend`: ``IMPROVING``, ``STABLE``, or ``DECLINING``.
        """
        history = profile._score_history
        if len(history) < 2:
            return TrustTrend.STABLE

        delta = history[-1] - history[0]
        if delta > _TREND_STABILITY_THRESHOLD:
            return TrustTrend.IMPROVING
        if delta < -_TREND_STABILITY_THRESHOLD:
            return TrustTrend.DECLINING
        return TrustTrend.STABLE

    # =========================================================================
    # Storage helpers — swap these three methods to migrate to a database
    # =========================================================================

    def _store_profile(self, profile: AgentTrustProfile) -> None:
        """Persist *profile* to the backing store (upsert semantics).

        Args:
            profile: Profile to save.

        Note:
            TODO [STORAGE]: Replace this method body with an ORM upsert,
            a Redis HSET, or equivalent.
        """
        self._profiles[profile.agent_id] = profile

    def _fetch_profile(self, agent_id: str) -> Optional[AgentTrustProfile]:
        """Retrieve a profile from the backing store.

        Args:
            agent_id: Agent identifier to look up.

        Returns:
            :class:`AgentTrustProfile` or ``None`` if not found.

        Note:
            TODO [STORAGE]: Replace this method body with an ORM query or cache
            lookup.
        """
        return self._profiles.get(agent_id)

    def _fetch_all(self):
        """Yield every stored :class:`AgentTrustProfile`.

        Yields:
            :class:`AgentTrustProfile` instances.

        Note:
            TODO [STORAGE]: Replace with a paginated database cursor for large
            deployments.
        """
        yield from self._profiles.values()

    # =========================================================================
    # Private orchestration helpers
    # =========================================================================

    def _get_or_create(self, agent_id: str) -> AgentTrustProfile:
        """Return an existing profile or create and persist a fresh one.

        Assumes the caller holds :attr:`_lock`.

        Args:
            agent_id: Agent identifier.

        Returns:
            Existing or freshly created :class:`AgentTrustProfile`.
        """
        profile = self._fetch_profile(agent_id)
        if profile is None:
            profile = _create_profile(agent_id)
            self._store_profile(profile)
        return profile

    def _record_event(self, agent_id: str, event_type: str) -> AgentTrustProfile:
        """Core event-processing pipeline shared by all record_* methods.

        Workflow:

        1. Validate agent_id.
        2. Auto-register the agent if unknown.
        3. Increment the appropriate counter.
        4. Recompute all derived scores and metadata via :meth:`update_scores`.
        5. Persist the updated profile.
        6. Return the updated profile.

        Args:
            agent_id: Agent identifier.
            event_type: One of ``"success"``, ``"suspicious"``, ``"block"``.

        Returns:
            Updated :class:`AgentTrustProfile`.
        """
        _validate_agent_id(agent_id)
        with self._lock:
            profile = self._get_or_create(agent_id)

            # TODO [REPLAY]: Check for replay attacks before incrementing
            #                counters (e.g. nonce / idempotency-key validation).

            _increment_counter(profile, event_type)
            self.update_scores(profile)
            self._store_profile(profile)

            # TODO [AUDIT]: Emit a per-event audit record to the audit logger.

            return profile

    # =========================================================================
    # Score computation helpers
    # =========================================================================

    @staticmethod
    def _compute_behavior_score(profile: AgentTrustProfile) -> float:
        """Derive the behavioural sub-score from request counters.

        During the cold-start period (< :data:`_BEHAVIOR_COLD_START_THRESHOLD`
        total requests) the score is blended with the current ``trust_score``
        to avoid over-penalising an agent on its very first interactions.

        Formula (steady state)::

            behavior_score = success_rate

        Formula (cold start)::

            behavior_score = 0.6 × success_rate + 0.4 × trust_score

        Args:
            profile: Source profile.

        Returns:
            float: Behaviour score clamped to ``[0.0, 1.0]``.
        """
        rate = profile.success_rate
        if profile.total_requests < _BEHAVIOR_COLD_START_THRESHOLD:
            score = 0.6 * rate + 0.4 * profile.trust_score
        else:
            score = rate
        return _clamp(score)

    @staticmethod
    def _compute_policy_score(profile: AgentTrustProfile) -> float:
        """Derive the policy-compliance sub-score from violation counters.

        A ``_POLICY_VIOLATION_MULTIPLIER`` amplifies the violation rate so that
        a sustained pattern of violations produces a rapid score drop.

        Formula::

            policy_score = max(1.0 - violation_rate × multiplier, 0.0)

        Args:
            profile: Source profile.

        Returns:
            float: Policy score clamped to ``[0.0, 1.0]``.
        """
        score = 1.0 - (profile.violation_rate * _POLICY_VIOLATION_MULTIPLIER)
        return _clamp(score)

    @staticmethod
    def _composite_trust_score(
        history_score: float,
        behavior_score: float,
        policy_score: float,
    ) -> float:
        """Compute the composite ``trust_score`` from its three inputs.

        This is the **single point of truth** for the weighting formula.
        Replace the body of this method to change the scoring model without
        modifying any other code.

        Current formula::

            trust = W_HISTORY × history
                  + W_BEHAVIOR × behavior
                  + W_POLICY   × policy

        Weights: history=0.40, behavior=0.35, policy=0.25.
        All weights sum to 1.0.

        Args:
            history_score: The agent's trust score *before* this event
                (provides score inertia / momentum).
            behavior_score: Freshly computed behavioural sub-score.
            policy_score: Freshly computed policy-compliance sub-score.

        Returns:
            float: Composite trust score clamped to ``[0.0, 1.0]``.

        Note:
            TODO [DECAY]: Multiply *history_score* by a time-decay coefficient
            before combining so that inactive agents gradually drift toward a
            neutral prior.
        """
        composite = (
            _WEIGHT_HISTORY * history_score
            + _WEIGHT_BEHAVIOR * behavior_score
            + _WEIGHT_POLICY * policy_score
        )
        return _clamp(composite)

    @staticmethod
    def _push_score_history(profile: AgentTrustProfile) -> None:
        """Append the current trust score to the history ring-buffer.

        Evicts the oldest entry when the buffer exceeds :data:`_TREND_WINDOW`.

        Args:
            profile: Profile whose history to update.

        Note:
            TODO [FINGERPRINT]: Each snapshot could be enriched with a
            timestamp and event-type tag to enable time-series anomaly
            detection.
        """
        profile._score_history.append(profile.trust_score)
        if len(profile._score_history) > _TREND_WINDOW:
            profile._score_history.pop(0)


# ============================================================================
# Module-level helpers (stateless, easily unit-testable)
# ============================================================================


def _create_profile(agent_id: str) -> AgentTrustProfile:
    """Construct a fresh :class:`AgentTrustProfile` for *agent_id*.

    The initial grade is derived from :data:`_INITIAL_TRUST_SCORE` so the
    profile is internally consistent from the moment of creation.

    Args:
        agent_id: Unique agent identifier.

    Returns:
        New :class:`AgentTrustProfile` with ``status=TrustStatus.NEW``.

    Note:
        TODO [IDENTITY]: Insert cryptographic identity verification here before
        accepting the agent_id as authoritative.

        TODO [SYBIL]: Cross-reference the agent_id against known Sybil clusters
        before issuing a trust profile.
    """
    from app.core.trust_engine import _GRADE_THRESHOLDS  # local import avoids circular ref

    # Compute initial grade from the initial trust score.
    initial_grade = "A"
    for threshold, grade in _GRADE_THRESHOLDS:
        if _INITIAL_TRUST_SCORE >= threshold:
            initial_grade = grade
            break

    return AgentTrustProfile(
        agent_id=agent_id,
        trust_score=_INITIAL_TRUST_SCORE,
        behavior_score=_INITIAL_BEHAVIOR_SCORE,
        policy_score=_INITIAL_POLICY_SCORE,
        security_grade=initial_grade,
        status=TrustStatus.NEW,
        trend=TrustTrend.STABLE,
    )


def _increment_counter(profile: AgentTrustProfile, event_type: str) -> None:
    """Increment the counter on *profile* that corresponds to *event_type*.

    Args:
        profile: Profile to mutate.
        event_type: One of ``"success"``, ``"suspicious"``, ``"block"``.

    Raises:
        ValueError: If *event_type* is not one of the recognised values.
    """
    if event_type == "success":
        profile.successful_requests += 1
    elif event_type == "suspicious":
        profile.suspicious_requests += 1
    elif event_type == "block":
        profile.blocked_requests += 1
    else:
        raise ValueError(f"Unknown event_type: {event_type!r}")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* into the closed interval ``[lo, hi]``.

    Args:
        value: The float to clamp.
        lo: Lower bound (default ``0.0``).
        hi: Upper bound (default ``1.0``).

    Returns:
        float: The clamped value.
    """
    return min(max(value, lo), hi)


def _validate_agent_id(agent_id: str) -> None:
    """Raise :exc:`ValueError` if *agent_id* is not a non-empty string.

    Args:
        agent_id: Value to validate.

    Raises:
        ValueError: If *agent_id* is empty, whitespace-only, or not a string.
    """
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError(
            f"agent_id must be a non-empty string; got {agent_id!r}"
        )
