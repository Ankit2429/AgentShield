"""Behavioral DNA Engine for AgentShield X.

This module implements **explainable statistical profiling** for every AI agent
observed by the platform.  It learns each agent's normal operating envelope
from historical observations and measures how much any new observation deviates
from that baseline.

It is deliberately **not machine learning**.  Every metric is a transparent
statistic (mean, standard deviation, frequency count) so that a human analyst
can fully understand and audit how the deviation score was produced.

Architecture overview
---------------------
::

    ┌────────────────────────────────────────────────────────────────────┐
    │                       BehaviorDNAEngine                            │
    │                                                                    │
    │  register_observation(agent_id, obs)                               │
    │       └─► _update_profile(profile, obs)                           │
    │              ├─ _update_tool_frequency()                           │
    │              ├─ _update_message_length()                           │
    │              ├─ _update_request_interval()                         │
    │              ├─ _update_threat_categories()                        │
    │              ├─ _update_risk_baseline()                            │
    │              └─ _recompute_fingerprint()  ◄── stable identity hash │
    │                                                                    │
    │  analyze_behavior(agent_id, obs)                                   │
    │       └─► _compute_analysis(profile, obs)                         │
    │              ├─ _score_tool_similarity()                           │
    │              ├─ _score_message_length_deviation()                  │
    │              ├─ _score_risk_deviation()                            │
    │              ├─ _score_threat_category_deviation()                 │
    │              ├─ _score_interval_deviation()                        │
    │              ├─ _merge_signal_scores()  ◄── weighted composite     │
    │              ├─ _classify_deviation_level()                        │
    │              └─ _build_reasons() + _build_summary()               │
    └────────────────────────────────────────────────────────────────────┘

Data flow with other engines::

    DetectionEngine ──► DetectionResult  ─┐
    (detection categories + risk score)    ├──► BehaviorObservation
    TrustEngine     ──► AgentTrustProfile  │        │
    (optional)                             │        ▼
                                           └──► BehaviorDNAEngine
                                                    │
                                                    ▼
                                              BehaviorAnalysis
                                                    │
                                                    └──► DecisionEngine (future [FINGERPRINT] hook)

Future extension points (marked with TODO throughout the file):
- ``[SEQUENCE]``    Analyse ordered sequences of tool calls for attack-chain detection.
- ``[GRAPH]``       Build a graph of agent↔tool and agent↔category co-occurrence.
- ``[EMBEDDING]``   Encode behavioral profiles as dense vectors for similarity search.
- ``[ANOMALY]``     Plug in an unsupervised anomaly detector (Isolation Forest etc.).
- ``[ONLINE]``      Replace batch statistics with Welford online mean/variance updates.
- ``[CROSS_AGENT]`` Correlate profiles across agents to detect coordinated behaviour.

Typical usage::

    from app.core.behavior_dna import BehaviorDNAEngine, BehaviorObservation

    dna = BehaviorDNAEngine()

    # Feed observations (typically after each DetectionEngine call)
    dna.register_observation(
        agent_id="agent-42",
        observation=BehaviorObservation(
            requested_tool="file_read",
            message_length=320,
            risk_score=0.12,
            threat_categories=["path_traversal"],
            timestamp=datetime.now(timezone.utc),
        ),
    )

    # Later, compare a new observation against the learnt profile
    analysis = dna.analyze_behavior(
        agent_id="agent-42",
        observation=BehaviorObservation(
            requested_tool="shell_exec",
            message_length=2400,
            risk_score=0.92,
            threat_categories=["command_injection", "code_execution"],
            timestamp=datetime.now(timezone.utc),
        ),
    )
    print(analysis.deviation_level, analysis.behavior_deviation)
    print(analysis.reasons)
"""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ============================================================================
# Enumerations
# ============================================================================


class DeviationLevel(str, Enum):
    """Qualitative classification of a behavioural deviation score.

    Attributes:
        NORMAL: Behaviour is fully consistent with the established baseline.
        SLIGHT: Minor deviation; within expected variance.
        MODERATE: Noticeable deviation; merits closer attention.
        HIGH: Significant deviation; likely outside normal operating range.
        CRITICAL: Extreme deviation; strong indicator of compromise or misuse.
    """

    NORMAL = "NORMAL"
    SLIGHT = "SLIGHT"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================================
# Tunable constants
# ============================================================================

# ── Minimum observations before the baseline is considered reliable ───────────
_MIN_OBSERVATIONS_FOR_BASELINE: int = 3

# ── Deviation-level thresholds (lower bound inclusive, ascending) ─────────────
_DEVIATION_LEVEL_THRESHOLDS: list[tuple[float, DeviationLevel]] = [
    (0.80, DeviationLevel.CRITICAL),
    (0.60, DeviationLevel.HIGH),
    (0.40, DeviationLevel.MODERATE),
    (0.20, DeviationLevel.SLIGHT),
    (0.00, DeviationLevel.NORMAL),
]

# ── Signal weights for composite similarity / deviation scores ────────────────
# These four values must sum to 1.0.
# Modify ONLY _merge_signal_scores() to change the weighting model.
_WEIGHT_TOOL: float = 0.30
_WEIGHT_MESSAGE_LENGTH: float = 0.20
_WEIGHT_RISK: float = 0.30
_WEIGHT_THREAT_CATEGORY: float = 0.20

# ── Message-length deviation sensitivity ────────────────────────────────────
# A message that is this many multiples of the average length is "fully deviant".
_MSG_LEN_SATURATION_RATIO: float = 5.0

# ── Risk deviation sensitivity ────────────────────────────────────────────────
# An absolute risk delta this large (or greater) counts as fully deviant.
_RISK_SATURATION_DELTA: float = 0.50

# ── Interval deviation sensitivity ───────────────────────────────────────────
# A request interval this many times shorter than average is "fully deviant".
_INTERVAL_SATURATION_RATIO: float = 10.0

# ── Reason-text templates ─────────────────────────────────────────────────────
# Used by _build_reasons() to produce human-readable deviation explanations.
_REASON_UNSEEN_TOOL = "Tool '{tool}' has never been seen in this agent's history"
_REASON_RARE_TOOL = "Tool '{tool}' is rarely used (seen in {pct:.0%} of requests)"
_REASON_MSG_LEN_HIGH = (
    "Message length ({length} chars) is {ratio:.1f}× above the agent's normal "
    "average ({avg:.0f} chars)"
)
_REASON_MSG_LEN_LOW = (
    "Message length ({length} chars) is {ratio:.1f}× below the agent's normal "
    "average ({avg:.0f} chars)"
)
_REASON_RISK_HIGH = (
    "Risk score ({risk:.2f}) is {delta:.2f} above the agent's normal "
    "baseline ({baseline:.2f})"
)
_REASON_RISK_LOW = (
    "Risk score ({risk:.2f}) is {delta:.2f} below the agent's normal "
    "baseline ({baseline:.2f})"
)
_REASON_UNSEEN_CATEGORY = "Threat category '{cat}' has not been seen in this agent's history"
_REASON_INTERVAL_SHORT = (
    "Request interval ({interval:.1f}s) is {ratio:.1f}× shorter than normal "
    "({avg:.1f}s); possible burst or replay"
)

# ── Reason-triggering thresholds ─────────────────────────────────────────────
# Tool frequency below this → "rarely used" reason.
_RARE_TOOL_THRESHOLD: float = 0.05
# Message length ratio above this → length reason triggered.
_MSG_LEN_REASON_THRESHOLD: float = 2.0
# Risk delta above this → risk reason triggered.
_RISK_REASON_THRESHOLD: float = 0.20
# Interval ratio above this (i.e. interval is <1/N of normal) → burst reason.
_INTERVAL_BURST_RATIO: float = 5.0


# ============================================================================
# Input / output dataclasses
# ============================================================================


@dataclass
class BehaviorObservation:
    """A single observed interaction to be fed into the DNA engine.

    This is the standard input record produced after every agent request.
    Callers typically construct one from the outputs of the Detection Engine
    and the tool router.

    Attributes:
        requested_tool: The capability name the agent invoked, or ``None`` if
            the request was not tool-specific (e.g. a plain chat message).
        message_length: Character count of the agent's raw message text.
        risk_score: Aggregate risk score from the Detection Engine ``[0.0, 1.0]``.
        threat_categories: List of threat category strings (e.g.
            ``["command_injection", "prompt_injection"]``) found in the message.
            May be empty for clean requests.
        timestamp: UTC time when the request was received.

    Example::

        obs = BehaviorObservation(
            requested_tool="file_read",
            message_length=512,
            risk_score=0.05,
            threat_categories=[],
            timestamp=datetime.now(timezone.utc),
        )
    """

    requested_tool: Optional[str]
    message_length: int
    risk_score: float
    threat_categories: list[str]
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class BehaviorProfile:
    """Accumulated statistical baseline for a single AI agent.

    This profile is updated incrementally with every call to
    :meth:`BehaviorDNAEngine.register_observation`.  All statistics are
    computed from the raw counters so they remain auditable.

    Attributes:
        agent_id: Unique, stable identifier for this agent.
        fingerprint_id: A short hex digest that reflects the agent's current
            behavioral pattern.  Recomputed after every observation; stabilises
            once the baseline converges.
        observations: Total number of observations recorded.
        tool_usage_frequency: Mapping of ``tool_name → observation_count``.
            A missing key means the tool has never been used.
        average_message_length: Rolling mean of message character counts.
        average_request_interval: Rolling mean of seconds between consecutive
            requests.  ``0.0`` until at least two observations exist.
        common_threat_categories: Mapping of ``category → observation_count``
            for every threat category seen across all observations.
        normal_risk_score: Rolling mean of risk scores across all observations.
        last_updated: UTC timestamp of the most recent observation.
        _last_timestamp: Internal: timestamp of the previous observation, used
            to compute inter-request intervals.  Not part of the public API.
        _total_message_length: Internal: running sum for mean computation.
        _total_risk_score: Internal: running sum for mean computation.
        _total_interval_seconds: Internal: running sum for mean computation.
        _interval_count: Internal: number of intervals recorded (= observations - 1).

    Example::

        profile = BehaviorProfile(agent_id="agent-7")
        print(profile.fingerprint_id)  # initial fingerprint
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    agent_id: str
    fingerprint_id: str = ""

    # ── Counters and aggregates ───────────────────────────────────────────────
    observations: int = 0
    tool_usage_frequency: dict[str, int] = field(default_factory=dict)
    average_message_length: float = 0.0
    average_request_interval: float = 0.0
    common_threat_categories: dict[str, int] = field(default_factory=dict)
    normal_risk_score: float = 0.0

    # ── Timestamps ───────────────────────────────────────────────────────────
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ── Internal accumulators (not for external consumers) ────────────────────
    _last_timestamp: Optional[datetime] = field(default=None, repr=False)
    _total_message_length: float = field(default=0.0, repr=False)
    _total_risk_score: float = field(default=0.0, repr=False)
    _total_interval_seconds: float = field(default=0.0, repr=False)
    _interval_count: int = field(default=0, repr=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Derived properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def is_baseline_established(self) -> bool:
        """Return ``True`` once enough observations exist for reliable analysis.

        Returns:
            bool: ``True`` when :attr:`observations` ≥
            :data:`_MIN_OBSERVATIONS_FOR_BASELINE`.
        """
        return self.observations >= _MIN_OBSERVATIONS_FOR_BASELINE

    @property
    def total_tool_uses(self) -> int:
        """Total number of observations that included a tool request.

        Returns:
            int: Sum of all values in :attr:`tool_usage_frequency`.
        """
        return sum(self.tool_usage_frequency.values())

    def tool_frequency_ratio(self, tool: str) -> float:
        """Return the fraction of tool-bearing observations that used *tool*.

        Args:
            tool: Tool name to look up.

        Returns:
            float: Value in ``[0.0, 1.0]``.  ``0.0`` if tool has never been
            used or if no tool observations exist yet.
        """
        total = self.total_tool_uses
        if total == 0:
            return 0.0
        return self.tool_usage_frequency.get(tool, 0) / total


@dataclass
class BehaviorAnalysis:
    """Result of comparing a single observation against an agent's baseline.

    Attributes:
        behavior_similarity: How closely the new observation matches the
            established profile.  ``1.0`` = perfectly normal; ``0.0`` =
            completely alien behaviour.
        behavior_deviation: Complement of ``behavior_similarity``
            (``= 1.0 - behavior_similarity``).  Higher is more alarming.
        deviation_level: Qualitative :class:`DeviationLevel` classification.
        reasons: Ordered list of human-readable strings explaining *why* a
            deviation was detected.  Empty for fully normal observations.
        summary: A single sentence summarising the analysis outcome.

    Example::

        analysis = engine.analyze_behavior("agent-42", obs)
        print(analysis.deviation_level)   # DeviationLevel.HIGH
        print(analysis.reasons[0])        # "Tool 'shell_exec' has never been seen..."
    """

    behavior_similarity: float
    behavior_deviation: float
    deviation_level: DeviationLevel
    reasons: list[str]
    summary: str


# ============================================================================
# Behavioral DNA Engine
# ============================================================================


class BehaviorDNAEngine:
    """Explainable statistical behavioral profiling engine for AI agents.

    The engine maintains a :class:`BehaviorProfile` for every agent it has
    observed and uses it as a baseline when evaluating new observations.

    Profiling is entirely statistics-based (no model weights, no black boxes).
    Every score can be traced back to a specific metric and threshold, making
    the engine fully auditable by security analysts.

    Thread safety
    -------------
    A :class:`threading.RLock` serialises all profile reads and writes.

    Singleton usage
    ---------------
    Instantiate once at application startup::

        dna_engine = BehaviorDNAEngine()

    Database migration
    ------------------
    Replace :meth:`_store_profile` / :meth:`_fetch_profile` /
    :meth:`_fetch_all` to migrate from in-memory to persistent storage.

    Example::

        dna = BehaviorDNAEngine()
        dna.register_observation("agent-1", obs)
        analysis = dna.analyze_behavior("agent-1", new_obs)
    """

    def __init__(self) -> None:
        """Initialise the engine with an empty in-memory profile store."""
        # TODO [ONLINE]: Replace the dict with a streaming profile store that
        #                supports concurrent writes from multiple workers.
        self._profiles: dict[str, BehaviorProfile] = {}
        self._lock: threading.RLock = threading.RLock()

    # =========================================================================
    # Public API
    # =========================================================================

    def register_observation(
        self,
        agent_id: str,
        observation: BehaviorObservation,
    ) -> BehaviorProfile:
        """Record a new observation and update the agent's behavioral baseline.

        Auto-registers the agent if it has not been seen before.

        Args:
            agent_id: Unique, stable agent identifier.
            observation: The :class:`BehaviorObservation` to incorporate.

        Returns:
            The updated :class:`BehaviorProfile` for *agent_id*.

        Raises:
            ValueError: If *agent_id* is empty or not a string.

        Example::

            profile = dna.register_observation("agent-1", obs)
            print(profile.observations)   # 1
            print(profile.fingerprint_id) # "a3f8..."
        """
        _validate_agent_id(agent_id)
        with self._lock:
            profile = self._get_or_create(agent_id)
            
            # Behavioral Poisoning Mitigation:
            # Ignore suspicious or malicious observations during profile training
            if observation.risk_score <= 0.30 and not observation.threat_categories:
                self._update_profile(profile, observation)
                self._store_profile(profile)
            else:
                # Still record count of requests, but do not shift average weights
                profile.observations += 1
                profile._last_timestamp = observation.timestamp
                profile.last_updated = datetime.now(timezone.utc)
                self._store_profile(profile)
                
            return profile

    def analyze_behavior(
        self,
        agent_id: str,
        observation: BehaviorObservation,
    ) -> BehaviorAnalysis:
        """Compare *observation* against the agent's established baseline.

        If the agent is unknown or has fewer than
        :data:`_MIN_OBSERVATIONS_FOR_BASELINE` observations, the analysis
        returns a ``NORMAL`` result with a note that the baseline is not yet
        established (benefit-of-the-doubt).

        This method is **read-only**: it does not modify the profile.  Call
        :meth:`register_observation` separately to incorporate the observation
        into the baseline.

        Args:
            agent_id: Unique, stable agent identifier.
            observation: The :class:`BehaviorObservation` to evaluate.

        Returns:
            :class:`BehaviorAnalysis` with full deviation breakdown.

        Raises:
            ValueError: If *agent_id* is empty or not a string.

        Example::

            analysis = dna.analyze_behavior("agent-1", new_obs)
            print(analysis.deviation_level, analysis.behavior_deviation)
        """
        _validate_agent_id(agent_id)
        with self._lock:
            profile = self._fetch_profile(agent_id)

        if profile is None or not profile.is_baseline_established:
            return _insufficient_baseline_analysis()

        return self._compute_analysis(profile, observation)

    def get_profile(self, agent_id: str) -> Optional[BehaviorProfile]:
        """Return the behavioral profile for *agent_id*, or ``None`` if unknown.

        Args:
            agent_id: Agent identifier to look up.

        Returns:
            :class:`BehaviorProfile` if found, ``None`` otherwise.
        """
        _validate_agent_id(agent_id)
        with self._lock:
            return self._fetch_profile(agent_id)

    def all_profiles(self) -> list[BehaviorProfile]:
        """Return a snapshot of all tracked agent profiles.

        Returns:
            list[BehaviorProfile]: All profiles in unspecified order.
            The list is a copy; mutations do not affect internal state.
        """
        with self._lock:
            return list(self._fetch_all())

    # =========================================================================
    # Storage helpers — replace these three methods to migrate to a database
    # =========================================================================

    def _store_profile(self, profile: BehaviorProfile) -> None:
        """Persist *profile* to the backing store (upsert semantics).

        Args:
            profile: Profile to save.

        Note:
            TODO [ONLINE]: Replace with an async upsert to a time-series store
            (InfluxDB, TimescaleDB) for high-throughput deployments.
        """
        self._profiles[profile.agent_id] = profile

    def _fetch_profile(self, agent_id: str) -> Optional[BehaviorProfile]:
        """Retrieve a profile from the backing store.

        Args:
            agent_id: Agent identifier.

        Returns:
            :class:`BehaviorProfile` or ``None`` if not found.
        """
        return self._profiles.get(agent_id)

    def _fetch_all(self):
        """Yield every stored :class:`BehaviorProfile`.

        Yields:
            :class:`BehaviorProfile` instances.
        """
        yield from self._profiles.values()

    # =========================================================================
    # Profile management
    # =========================================================================

    def _get_or_create(self, agent_id: str) -> BehaviorProfile:
        """Return an existing profile or create and persist a fresh one.

        Assumes the caller holds :attr:`_lock`.

        Args:
            agent_id: Agent identifier.

        Returns:
            Existing or freshly created :class:`BehaviorProfile`.
        """
        profile = self._fetch_profile(agent_id)
        if profile is None:
            profile = BehaviorProfile(agent_id=agent_id)
            profile.fingerprint_id = _compute_fingerprint(profile)
            self._store_profile(profile)
        return profile

    # =========================================================================
    # Profile update pipeline
    # =========================================================================

    @staticmethod
    def _update_profile(
        profile: BehaviorProfile,
        obs: BehaviorObservation,
    ) -> None:
        """Incorporate *obs* into *profile* in-place.

        Update order matters: interval must be computed before
        ``_last_timestamp`` is overwritten.

        Args:
            profile: Profile to mutate.
            obs: The new observation to incorporate.
        """
        BehaviorDNAEngine._update_request_interval(profile, obs.timestamp)
        BehaviorDNAEngine._update_tool_frequency(profile, obs.requested_tool)
        BehaviorDNAEngine._update_message_length(profile, obs.message_length)
        BehaviorDNAEngine._update_risk_baseline(profile, obs.risk_score)
        BehaviorDNAEngine._update_threat_categories(profile, obs.threat_categories)

        profile.observations += 1
        profile._last_timestamp = obs.timestamp
        profile.last_updated = datetime.now(timezone.utc)

        # Recompute fingerprint after every update so it reflects current state.
        profile.fingerprint_id = _compute_fingerprint(profile)

    @staticmethod
    def _update_tool_frequency(
        profile: BehaviorProfile,
        tool: Optional[str],
    ) -> None:
        """Increment the observation counter for *tool* in the profile.

        Args:
            profile: Profile to mutate.
            tool: Tool name, or ``None`` if no tool was requested.
        """
        if tool is not None:
            normalized = tool.lower().strip()
            profile.tool_usage_frequency[normalized] = (
                profile.tool_usage_frequency.get(normalized, 0) + 1
            )

    @staticmethod
    def _update_message_length(profile: BehaviorProfile, length: int) -> None:
        """Update the rolling mean of message lengths.

        Uses a cumulative-sum approach:
        ``average = total_length / observations``.

        Args:
            profile: Profile to mutate.
            length: Character count of the current message.
        """
        profile._total_message_length += length
        # Recalculate mean using the incremented observation count (+1 applied
        # after this call in _update_profile).
        profile.average_message_length = profile._total_message_length / (
            profile.observations + 1
        )

    @staticmethod
    def _update_request_interval(
        profile: BehaviorProfile,
        timestamp: datetime,
    ) -> None:
        """Update the rolling mean of inter-request intervals.

        Only computes an interval when a previous timestamp exists.

        Args:
            profile: Profile to mutate.
            timestamp: Current request timestamp.

        Note:
            TODO [SEQUENCE]: Store the full timestamp sequence to enable
            burst-pattern and cadence-anomaly analysis.
        """
        if profile._last_timestamp is not None:
            delta = (timestamp - profile._last_timestamp).total_seconds()
            if delta >= 0:  # Guard against clock skew.
                profile._total_interval_seconds += delta
                profile._interval_count += 1
                profile.average_request_interval = (
                    profile._total_interval_seconds / profile._interval_count
                )

    @staticmethod
    def _update_risk_baseline(profile: BehaviorProfile, risk_score: float) -> None:
        """Update the rolling mean of risk scores.

        Args:
            profile: Profile to mutate.
            risk_score: Detection Engine risk score for the current request.
        """
        profile._total_risk_score += risk_score
        profile.normal_risk_score = profile._total_risk_score / (
            profile.observations + 1
        )

    @staticmethod
    def _update_threat_categories(
        profile: BehaviorProfile,
        categories: list[str],
    ) -> None:
        """Increment observation counters for each threat category in *categories*.

        Args:
            profile: Profile to mutate.
            categories: Threat category strings from the Detection Engine.
        """
        for category in categories:
            normalized = category.lower().strip()
            profile.common_threat_categories[normalized] = (
                profile.common_threat_categories.get(normalized, 0) + 1
            )

    # =========================================================================
    # Deviation analysis pipeline
    # =========================================================================

    def _compute_analysis(
        self,
        profile: BehaviorProfile,
        obs: BehaviorObservation,
    ) -> BehaviorAnalysis:
        """Produce a full :class:`BehaviorAnalysis` for *obs* against *profile*.

        Orchestrates the five signal scorers, merges them, classifies the
        deviation level, and assembles the human-readable output.

        Args:
            profile: Established behavioral profile (baseline).
            obs: New observation to evaluate.

        Returns:
            Completed :class:`BehaviorAnalysis`.
        """
        tool = obs.requested_tool.lower().strip() if obs.requested_tool else None

        tool_score = self._score_tool_similarity(profile, tool)
        length_score = self._score_message_length_similarity(
            profile, obs.message_length
        )
        risk_score = self._score_risk_similarity(profile, obs.risk_score)
        category_score = self._score_threat_category_similarity(
            profile, obs.threat_categories
        )
        # Interval score is advisory-only for now; included as context.
        interval_score = self._score_interval_similarity(
            profile, obs.timestamp
        )

        similarity = self._merge_signal_scores(
            tool_score=tool_score,
            length_score=length_score,
            risk_score=risk_score,
            category_score=category_score,
        )
        deviation = _clamp(1.0 - similarity)
        level = _classify_deviation_level(deviation)

        reasons = self._build_reasons(
            profile=profile,
            obs=obs,
            tool=tool,
            tool_score=tool_score,
            length_score=length_score,
            risk_score_signal=risk_score,
            interval_score=interval_score,
        )
        summary = _build_summary(
            deviation=deviation,
            level=level,
            reason_count=len(reasons),
            observations=profile.observations,
        )

        return BehaviorAnalysis(
            behavior_similarity=round(similarity, 4),
            behavior_deviation=round(deviation, 4),
            deviation_level=level,
            reasons=reasons,
            summary=summary,
        )

    # ── Individual signal scorers (each returns similarity in [0.0, 1.0]) ─────

    @staticmethod
    def _score_tool_similarity(
        profile: BehaviorProfile,
        tool: Optional[str],
    ) -> float:
        """Compute how well *tool* matches the agent's historical tool usage.

        Scoring:
        * No tool in observation, no tools in history → 1.0 (neutral match).
        * Tool used before → its frequency ratio (common tools score higher).
        * Tool never seen before → 0.0.

        Args:
            profile: Agent's behavioral profile.
            tool: Normalised tool name, or ``None``.

        Returns:
            float: Similarity score in ``[0.0, 1.0]``.

        Note:
            TODO [GRAPH]: Model tool co-occurrence to detect unusual
            *combinations* of tools, not just individual outliers.
        """
        if tool is None:
            return 1.0 if profile.total_tool_uses == 0 else 0.8
        return profile.tool_frequency_ratio(tool)

    @staticmethod
    def _score_message_length_similarity(
        profile: BehaviorProfile,
        length: int,
    ) -> float:
        """Compute similarity between *length* and the agent's average length.

        Uses a normalised ratio that saturates at :data:`_MSG_LEN_SATURATION_RATIO`
        so that a message 10× longer than normal is not meaningfully "worse"
        than one 6× longer from a scoring perspective.

        Args:
            profile: Agent's behavioral profile.
            length: Character count of the current message.

        Returns:
            float: Similarity score in ``[0.0, 1.0]``.  ``1.0`` when the
            length exactly matches the average.
        """
        avg = profile.average_message_length
        if avg <= 0:
            return 1.0  # No baseline yet — neutral.

        ratio = max(length, avg) / max(min(length, avg), 1)
        # Normalise: ratio of 1.0 → similarity 1.0; saturation → similarity 0.0.
        deviation_fraction = min((ratio - 1.0) / (_MSG_LEN_SATURATION_RATIO - 1.0), 1.0)
        return _clamp(1.0 - deviation_fraction)

    @staticmethod
    def _score_risk_similarity(
        profile: BehaviorProfile,
        risk_score: float,
    ) -> float:
        """Compute similarity between *risk_score* and the agent's baseline risk.

        The absolute delta is normalised against :data:`_RISK_SATURATION_DELTA`.

        Args:
            profile: Agent's behavioral profile.
            risk_score: Detection Engine risk score for the current request.

        Returns:
            float: Similarity score in ``[0.0, 1.0]``.
        """
        baseline = profile.normal_risk_score
        delta = abs(risk_score - baseline)
        deviation_fraction = min(delta / _RISK_SATURATION_DELTA, 1.0)
        return _clamp(1.0 - deviation_fraction)

    @staticmethod
    def _score_threat_category_similarity(
        profile: BehaviorProfile,
        categories: list[str],
    ) -> float:
        """Compute similarity between the observed threat categories and the profile.

        Scoring:
        * No categories in observation, none in history → 1.0.
        * All categories seen before → 1.0.
        * Some categories never seen → proportion of unseen categories reduces score.
        * All categories are new → 0.0.

        Args:
            profile: Agent's behavioral profile.
            categories: Threat categories from the Detection Engine.

        Returns:
            float: Similarity score in ``[0.0, 1.0]``.

        Note:
            TODO [EMBEDDING]: Encode categories as semantic vectors so that
            "command_injection" and "code_execution" are recognised as
            related (high semantic overlap) rather than treated as fully
            independent signals.
        """
        if not categories:
            return 1.0 if not profile.common_threat_categories else 1.0

        known = profile.common_threat_categories
        seen_count = sum(
            1 for c in categories if c.lower().strip() in known
        )
        return seen_count / len(categories)

    @staticmethod
    def _score_interval_similarity(
        profile: BehaviorProfile,
        timestamp: datetime,
    ) -> float:
        """Compute similarity of the current request interval against baseline.

        A very short interval (burst) is flagged as deviant.  An unusually
        long interval is not penalised (agents can go quiet legitimately).

        Args:
            profile: Agent's behavioral profile.
            timestamp: Timestamp of the current request.

        Returns:
            float: Similarity score in ``[0.0, 1.0]``.

        Note:
            TODO [SEQUENCE]: Track cumulative burst windows (e.g. 10 requests
            in 1 second) rather than single-interval comparisons.
        """
        avg = profile.average_request_interval
        if avg <= 0 or profile._last_timestamp is None:
            return 1.0  # No baseline yet — neutral.

        elapsed = (timestamp - profile._last_timestamp).total_seconds()
        if elapsed <= 0:
            return 0.0  # Zero or negative elapsed → extreme burst.

        ratio = avg / elapsed  # >1 means faster than average.
        deviation_fraction = min((ratio - 1.0) / (_INTERVAL_SATURATION_RATIO - 1.0), 1.0)
        return _clamp(1.0 - max(deviation_fraction, 0.0))

    # ── Composite signal merger ───────────────────────────────────────────────

    @staticmethod
    def _merge_signal_scores(
        tool_score: float,
        length_score: float,
        risk_score: float,
        category_score: float,
    ) -> float:
        """Combine individual signal similarity scores into one composite score.

        This is the **single point of truth** for the weighting formula.
        Swap the body of this method to change the merging strategy without
        touching any other code.

        Current formula::

            similarity = W_TOOL     × tool_score
                       + W_LENGTH   × length_score
                       + W_RISK     × risk_score
                       + W_CATEGORY × category_score

        Weights: tool=0.30, length=0.20, risk=0.30, category=0.20.

        Args:
            tool_score: Similarity from :meth:`_score_tool_similarity`.
            length_score: Similarity from :meth:`_score_message_length_similarity`.
            risk_score: Similarity from :meth:`_score_risk_similarity`.
            category_score: Similarity from :meth:`_score_threat_category_similarity`.

        Returns:
            float: Composite similarity score in ``[0.0, 1.0]``.

        Note:
            TODO [ANOMALY]: Replace the weighted average with an unsupervised
            anomaly detector (e.g. Isolation Forest, One-Class SVM) trained
            on historical observations.

            TODO [CROSS_AGENT]: Incorporate a cross-agent population baseline
            so that unusual behaviour relative to *all* agents is also captured.
        """
        composite = (
            _WEIGHT_TOOL * tool_score
            + _WEIGHT_MESSAGE_LENGTH * length_score
            + _WEIGHT_RISK * risk_score
            + _WEIGHT_THREAT_CATEGORY * category_score
        )
        return _clamp(composite)

    # ── Reason and summary builders ───────────────────────────────────────────

    def _build_reasons(
        self,
        profile: BehaviorProfile,
        obs: BehaviorObservation,
        tool: Optional[str],
        tool_score: float,
        length_score: float,
        risk_score_signal: float,
        interval_score: float,
    ) -> list[str]:
        """Build an ordered list of human-readable deviation reason strings.

        Only reasons whose corresponding signal score is below its threshold
        are included.  Reasons are ordered from most to least impactful.

        Args:
            profile: Agent's behavioral profile (baseline).
            obs: The observation being analysed.
            tool: Normalised tool name (may be ``None``).
            tool_score: Similarity score from tool evaluator.
            length_score: Similarity score from message-length evaluator.
            risk_score_signal: Similarity score from risk evaluator.
            interval_score: Similarity score from interval evaluator.

        Returns:
            list[str]: Human-readable reason strings.  Empty if no deviations
            exceeded their thresholds.
        """
        reasons: list[str] = []

        # ── Tool reasons ──────────────────────────────────────────────────────
        if tool is not None:
            if tool_score == 0.0:
                reasons.append(
                    _REASON_UNSEEN_TOOL.format(tool=obs.requested_tool)
                )
            elif tool_score < _RARE_TOOL_THRESHOLD:
                reasons.append(
                    _REASON_RARE_TOOL.format(
                        tool=obs.requested_tool,
                        pct=profile.tool_frequency_ratio(tool),
                    )
                )

        # ── Message-length reasons ─────────────────────────────────────────────
        avg_len = profile.average_message_length
        if avg_len > 0 and length_score < (1.0 - 1.0 / _MSG_LEN_REASON_THRESHOLD):
            ratio = obs.message_length / avg_len if avg_len > 0 else 1.0
            if obs.message_length > avg_len:
                reasons.append(
                    _REASON_MSG_LEN_HIGH.format(
                        length=obs.message_length,
                        ratio=ratio,
                        avg=avg_len,
                    )
                )
            elif avg_len > 0:
                reasons.append(
                    _REASON_MSG_LEN_LOW.format(
                        length=obs.message_length,
                        ratio=1.0 / ratio if ratio > 0 else 0,
                        avg=avg_len,
                    )
                )

        # ── Risk reasons ───────────────────────────────────────────────────────
        baseline_risk = profile.normal_risk_score
        risk_delta = obs.risk_score - baseline_risk
        if abs(risk_delta) >= _RISK_REASON_THRESHOLD:
            if risk_delta > 0:
                reasons.append(
                    _REASON_RISK_HIGH.format(
                        risk=obs.risk_score,
                        delta=risk_delta,
                        baseline=baseline_risk,
                    )
                )
            else:
                reasons.append(
                    _REASON_RISK_LOW.format(
                        risk=obs.risk_score,
                        delta=abs(risk_delta),
                        baseline=baseline_risk,
                    )
                )

        # ── Threat category reasons ────────────────────────────────────────────
        for cat in obs.threat_categories:
            norm = cat.lower().strip()
            if norm not in profile.common_threat_categories:
                reasons.append(_REASON_UNSEEN_CATEGORY.format(cat=cat))

        # ── Interval reasons ───────────────────────────────────────────────────
        avg_interval = profile.average_request_interval
        if (
            avg_interval > 0
            and profile._last_timestamp is not None
            and interval_score < 0.5
        ):
            elapsed = max(
                (obs.timestamp - profile._last_timestamp).total_seconds(), 0.001
            )
            ratio = avg_interval / elapsed
            if ratio >= _INTERVAL_BURST_RATIO:
                reasons.append(
                    _REASON_INTERVAL_SHORT.format(
                        interval=elapsed,
                        ratio=ratio,
                        avg=avg_interval,
                    )
                )

        return reasons


# ============================================================================
# Module-level pure helpers
# ============================================================================


def _compute_fingerprint(profile: BehaviorProfile) -> str:
    """Compute a short, stable hex fingerprint reflecting the profile's state.

    The fingerprint is derived from the top-3 most-used tools, the top-3 most
    common threat categories, the rounded average message length, and the
    rounded baseline risk score.  Minor fluctuations in rarely-used metrics
    do not change the fingerprint, providing stability once the baseline
    converges.

    Args:
        profile: The profile to fingerprint.

    Returns:
        str: 16-character lowercase hex string.

    Note:
        TODO [EMBEDDING]: Replace with a semantic embedding hash that captures
        relational structure (e.g. which tools tend to co-occur).
    """
    # Top-3 tools by frequency (deterministic sort for stability).
    top_tools = sorted(
        profile.tool_usage_frequency.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )[:3]

    # Top-3 threat categories by frequency.
    top_categories = sorted(
        profile.common_threat_categories.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )[:3]

    parts = (
        "|".join(t for t, _ in top_tools),
        "|".join(c for c, _ in top_categories),
        f"{round(profile.average_message_length, -2):.0f}",  # Rounded to 100s.
        f"{round(profile.normal_risk_score, 1):.1f}",
    )
    raw = ";".join(parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return digest[:16]


def _classify_deviation_level(deviation: float) -> DeviationLevel:
    """Map a numeric deviation score to a :class:`DeviationLevel`.

    Args:
        deviation: Value in ``[0.0, 1.0]`` where 1.0 is maximally deviant.

    Returns:
        :class:`DeviationLevel` for the given score.
    """
    for threshold, level in _DEVIATION_LEVEL_THRESHOLDS:
        if deviation >= threshold:
            return level
    return DeviationLevel.NORMAL


def _build_summary(
    deviation: float,
    level: DeviationLevel,
    reason_count: int,
    observations: int,
) -> str:
    """Compose a single-sentence summary of the analysis result.

    Args:
        deviation: Numeric deviation score.
        level: Qualitative deviation level.
        reason_count: Number of reasons generated.
        observations: Total observations in the profile.

    Returns:
        str: Human-readable summary sentence.
    """
    if level == DeviationLevel.NORMAL:
        return (
            f"Behavior is consistent with the established profile "
            f"({observations} observations, deviation {deviation:.0%})."
        )
    reason_phrase = (
        f"{reason_count} deviation signal{'s' if reason_count != 1 else ''}"
    )
    return (
        f"{level.value} behavioral deviation detected "
        f"({reason_phrase}, deviation {deviation:.0%}, "
        f"baseline built from {observations} observations)."
    )


def _insufficient_baseline_analysis() -> BehaviorAnalysis:
    """Return a neutral analysis when the baseline is not yet established.

    Returns:
        :class:`BehaviorAnalysis` with ``NORMAL`` deviation and an
        informational summary note.
    """
    return BehaviorAnalysis(
        behavior_similarity=1.0,
        behavior_deviation=0.0,
        deviation_level=DeviationLevel.NORMAL,
        reasons=[],
        summary=(
            f"Baseline not yet established "
            f"(minimum {_MIN_OBSERVATIONS_FOR_BASELINE} observations required); "
            f"observation accepted without deviation scoring."
        ),
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to ``[lo, hi]``.

    Args:
        value: Value to clamp.
        lo: Lower bound.
        hi: Upper bound.

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
