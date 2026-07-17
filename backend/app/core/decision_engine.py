"""Decision Intelligence Engine for AgentShield.

The Decision Engine is the **brain** of AgentShield.  It is a pure
aggregation and reasoning layer: it receives structured outputs from the
Detection Engine and the Trust Intelligence Engine, synthesises them, and
produces a fully-explainable security decision.

It never simply returns "allow" or "block".  Every output includes:

* A machine-readable ``decision`` and ``reasoning`` list.
* A human-readable ``recommendation`` and ``explanation`` sentence.
* Numeric ``confidence`` and ``risk_score`` values that are derived
  independently through transparent sub-evaluators.

Architecture overview
---------------------
::

    ┌─────────────────────────────────────────────────────────────────────┐
    │                        DecisionEngine.decide()                      │
    │                                                                     │
    │   Inputs:  DetectionResult  AgentTrustProfile  tool  context        │
    │                                                                     │
    │   ┌──────────────────────────────────────────────────────────────┐  │
    │   │                  _evaluate_*  sub-evaluators                 │  │
    │   │                                                              │  │
    │   │  _evaluate_risk()      → RiskFinding                        │  │
    │   │  _evaluate_trust()     → TrustFinding                       │  │
    │   │  _evaluate_behavior()  → BehaviorFinding                    │  │
    │   │  _evaluate_policy()    → PolicyFinding                      │  │
    │   │  _evaluate_tool()      → ToolFinding                        │  │
    │   └───────────────────────┬──────────────────────────────────────┘  │
    │                           ▼                                         │
    │              _merge_findings(findings)                              │
    │                           │                                         │
    │                           ▼                                         │
    │              _finalize_decision(merged)                             │
    │                           │                                         │
    │                           ▼                                         │
    │                     DecisionResult                                  │
    └─────────────────────────────────────────────────────────────────────┘

Future extension points (marked with TODO throughout the file):
- ``[MITRE]``       Map threat categories to MITRE ATT&CK technique IDs.
- ``[LLM]``         Replace _build_explanation() with an LLM reasoning call.
- ``[POLICY]``      Load decision rules from an external policy plugin/file.
- ``[THREAT_INTEL]``Enrich DetectionResult with threat intelligence feeds.
- ``[GRAPH]``       Correlate agent behaviour across a graph of relationships.
- ``[FINGERPRINT]`` Feed behavior deviation signals from a fingerprint store.
- ``[HISTORY]``     Persist and replay DecisionResult objects for audit trails.

Typical usage::

    from app.core.decision_engine import DecisionEngine
    from app.core.detector import DetectionEngine
    from app.core.trust_engine import TrustEngine

    detection  = DetectionEngine()
    trust      = TrustEngine()
    decisions  = DecisionEngine()

    det_result   = detection.analyze("ignore previous instructions; rm -rf /")
    trust_profile = trust.get_or_register("agent-42")

    result = decisions.decide(
        detection_result=det_result,
        trust_profile=trust_profile,
        requested_tool="shell_exec",
        context={"session_id": "s-001"},
    )

    print(result.decision, result.confidence, result.explanation)
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.core.models import DetectionResult
from app.core.severity import Severity
from app.core.trust_engine import AgentTrustProfile, TrustStatus, TrustTrend


# ============================================================================
# Enumerations
# ============================================================================


class Decision(str, Enum):
    """The outcome produced by the Decision Engine for a single request.

    Decisions are ordered from least to most restrictive.  Every decision
    level includes a mandatory explanation in the accompanying
    :class:`DecisionResult`.

    Attributes:
        ALLOW: Request is clean and the agent is trusted.  Proceed normally.
        ALLOW_WITH_WARNING: Request is borderline.  Allow but flag for review.
        MONITOR: Request is allowed; agent placed under heightened observation.
        REVIEW: Human review is required before the request proceeds.
        QUARANTINE: Agent is isolated; request is held pending investigation.
        BLOCK: Request is denied immediately.  Agent may be flagged.
    """

    ALLOW = "ALLOW"
    ALLOW_WITH_WARNING = "ALLOW_WITH_WARNING"
    MONITOR = "MONITOR"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"
    BLOCK = "BLOCK"


class DecisionSeverity(str, Enum):
    """Severity level assigned to a :class:`DecisionResult`.

    Mirrors the Detection Engine's :class:`~app.core.severity.Severity` but
    adds ``INFO`` for purely informational decisions.

    Attributes:
        INFO: No actionable threat; result is for telemetry only.
        LOW: Minor concern; minimal risk.
        MEDIUM: Noteworthy risk requiring monitoring.
        HIGH: Serious risk requiring immediate attention.
        CRITICAL: Severe threat; block or quarantine mandatory.
    """

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReasonCode(str, Enum):
    """Machine-readable reason codes attached to a :class:`DecisionResult`.

    Reason codes are non-exclusive — a single decision may carry multiple
    codes, each corresponding to a specific signal that contributed.

    Attributes:
        COMMAND_INJECTION: Shell command injection pattern detected.
        PROMPT_INJECTION: Prompt override / jailbreak pattern detected.
        SQL_INJECTION: SQL injection pattern detected.
        PATH_TRAVERSAL: Directory traversal pattern detected.
        CODE_EXECUTION: Arbitrary code execution pattern detected.
        NETWORK_EXFILTRATION: Data exfiltration network pattern detected.
        LOW_TRUST: Agent trust score is below the warning threshold.
        CRITICAL_TRUST: Agent trust score is critically low.
        DECLINING_TRUST: Agent trust score is trending downward.
        POLICY_VIOLATION: Agent has an elevated policy-violation rate.
        BEHAVIOR_DEVIATION: Agent behaviour score is abnormally low.
        UNAUTHORIZED_TOOL: Requested tool is not on the approved list.
        UNAUTHORIZED_TOOL_ACCESS: Requested tool violates capability matrix rules.
        SENSITIVE_TOOL: Requested tool is allowed but considered sensitive.
        UNKNOWN_AGENT: Agent has no interaction history (status NEW).
        BLOCKED_AGENT: Agent has previously been blocked by the platform.
        QUARANTINED_AGENT: Agent is currently under quarantine.
        CLEAN: No threat signals detected.
    """

    COMMAND_INJECTION = "COMMAND_INJECTION"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    SQL_INJECTION = "SQL_INJECTION"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"
    CODE_EXECUTION = "CODE_EXECUTION"
    NETWORK_EXFILTRATION = "NETWORK_EXFILTRATION"
    LOW_TRUST = "LOW_TRUST"
    CRITICAL_TRUST = "CRITICAL_TRUST"
    DECLINING_TRUST = "DECLINING_TRUST"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    BEHAVIOR_DEVIATION = "BEHAVIOR_DEVIATION"
    UNAUTHORIZED_TOOL = "UNAUTHORIZED_TOOL"
    UNAUTHORIZED_TOOL_ACCESS = "UNAUTHORIZED_TOOL_ACCESS"
    SENSITIVE_TOOL = "SENSITIVE_TOOL"
    UNKNOWN_AGENT = "UNKNOWN_AGENT"
    BLOCKED_AGENT = "BLOCKED_AGENT"
    QUARANTINED_AGENT = "QUARANTINED_AGENT"
    CLEAN = "CLEAN"


class Recommendation(str, Enum):
    """Human-friendly action recommendations returned in a :class:`DecisionResult`.

    Attributes:
        CONTINUE: No action required; proceed normally.
        MONITOR_AGENT: Increase observation frequency for this agent.
        REQUEST_HUMAN_REVIEW: Escalate to a human analyst for review.
        QUARANTINE_AGENT: Isolate agent and hold all pending requests.
        BLOCK_IMMEDIATELY: Deny request and revoke agent access.
        ROTATE_CREDENTIALS: Invalidate and reissue agent credentials.
        INVESTIGATE_AGENT: Launch a full forensic investigation.
    """

    CONTINUE = "Continue"
    MONITOR_AGENT = "Monitor Agent"
    REQUEST_HUMAN_REVIEW = "Request Human Review"
    QUARANTINE_AGENT = "Quarantine Agent"
    BLOCK_IMMEDIATELY = "Block Immediately"
    ROTATE_CREDENTIALS = "Rotate Credentials"
    INVESTIGATE_AGENT = "Investigate Agent"


# ============================================================================
# Tunable constants
# ============================================================================

# ── Risk evaluation ──────────────────────────────────────────────────────────
# Risk score above this triggers at minimum ALLOW_WITH_WARNING.
_RISK_WARN_THRESHOLD: float = 0.25
# Risk score above this triggers at minimum MONITOR.
_RISK_MONITOR_THRESHOLD: float = 0.45
# Risk score above this triggers REVIEW.
_RISK_REVIEW_THRESHOLD: float = 0.65
# Risk score above this triggers BLOCK.
_RISK_BLOCK_THRESHOLD: float = 0.80

# ── Trust evaluation ─────────────────────────────────────────────────────────
# Trust score below this triggers LOW_TRUST reason.
_TRUST_WARN_THRESHOLD: float = 0.70
# Trust score below this triggers CRITICAL_TRUST reason.
_TRUST_CRITICAL_THRESHOLD: float = 0.35

# ── Behavior evaluation ──────────────────────────────────────────────────────
# Behavior score below this triggers BEHAVIOR_DEVIATION.
_BEHAVIOR_DEVIATION_THRESHOLD: float = 0.50

# ── Policy evaluation ────────────────────────────────────────────────────────
# Policy score below this triggers POLICY_VIOLATION.
_POLICY_VIOLATION_THRESHOLD: float = 0.55

# ── Tool evaluation ──────────────────────────────────────────────────────────
# Tools on this list are blocked outright regardless of trust.
# TODO [POLICY]: Load from an external policy plugin or database at runtime.
_UNAUTHORIZED_TOOLS: frozenset[str] = frozenset({
    "shell_exec",
    "rm_rf",
    "format_disk",
    "drop_database",
    "exfil_upload",
    "bypass_auth",
    "escalate_privilege",
})

# Tools that are allowed but require heightened scrutiny.
# TODO [POLICY]: Load from an external policy plugin or database at runtime.
_SENSITIVE_TOOLS: frozenset[str] = frozenset({
    "file_read",
    "network_request",
    "code_eval",
    "subprocess_run",
    "db_query",
    "secret_access",
    "config_write",
})

# ── Confidence calculation ────────────────────────────────────────────────────
# Minimum threat count to reach full confidence from detection alone.
_CONFIDENCE_MAX_THREAT_COUNT: int = 5
# Weight of threat-count signal in overall confidence.
_CONFIDENCE_WEIGHT_THREATS: float = 0.40
# Weight of trust stability signal in overall confidence.
_CONFIDENCE_WEIGHT_TRUST_STABILITY: float = 0.35
# Weight of evidence consistency signal in overall confidence.
_CONFIDENCE_WEIGHT_CONSISTENCY: float = 0.25

# ── Threat-category → ReasonCode mapping ─────────────────────────────────────
# TODO [MITRE]: Add a third element mapping each category to a MITRE ATT&CK ID.
_CATEGORY_TO_REASON: dict[str, ReasonCode] = {
    "command_injection": ReasonCode.COMMAND_INJECTION,
    "prompt_injection": ReasonCode.PROMPT_INJECTION,
    "sql_injection": ReasonCode.SQL_INJECTION,
    "path_traversal": ReasonCode.PATH_TRAVERSAL,
    "code_execution": ReasonCode.CODE_EXECUTION,
    "network_exfiltration": ReasonCode.NETWORK_EXFILTRATION,
}

# ── Severity → DecisionSeverity mapping ──────────────────────────────────────
_SEVERITY_MAP: dict[Severity, DecisionSeverity] = {
    Severity.LOW: DecisionSeverity.LOW,
    Severity.MEDIUM: DecisionSeverity.MEDIUM,
    Severity.HIGH: DecisionSeverity.HIGH,
    Severity.CRITICAL: DecisionSeverity.CRITICAL,
}

# ── Decision → Recommendation default mapping ─────────────────────────────────
_DECISION_TO_RECOMMENDATION: dict[Decision, Recommendation] = {
    Decision.ALLOW: Recommendation.CONTINUE,
    Decision.ALLOW_WITH_WARNING: Recommendation.MONITOR_AGENT,
    Decision.MONITOR: Recommendation.MONITOR_AGENT,
    Decision.REVIEW: Recommendation.REQUEST_HUMAN_REVIEW,
    Decision.QUARANTINE: Recommendation.QUARANTINE_AGENT,
    Decision.BLOCK: Recommendation.BLOCK_IMMEDIATELY,
}


# ============================================================================
# Internal finding dataclasses (private to this module)
# ============================================================================


@dataclass
class _RiskFinding:
    """Output of :meth:`DecisionEngine._evaluate_risk`."""

    risk_score: float
    reasons: list[ReasonCode]
    peak_severity: DecisionSeverity
    threat_count: int


@dataclass
class _TrustFinding:
    """Output of :meth:`DecisionEngine._evaluate_trust`."""

    trust_score: float
    reasons: list[ReasonCode]
    is_blocked_agent: bool
    is_quarantined_agent: bool
    is_declining: bool


@dataclass
class _BehaviorFinding:
    """Output of :meth:`DecisionEngine._evaluate_behavior`."""

    behavior_score: float
    reasons: list[ReasonCode]


@dataclass
class _PolicyFinding:
    """Output of :meth:`DecisionEngine._evaluate_policy`."""

    policy_score: float
    reasons: list[ReasonCode]


@dataclass
class _ToolFinding:
    """Output of :meth:`DecisionEngine._evaluate_tool`."""

    requested_tool: Optional[str]
    reasons: list[ReasonCode]
    is_unauthorized: bool


@dataclass
class _MergedFindings:
    """Aggregated output of all sub-evaluators, fed into :meth:`~DecisionEngine._finalize_decision`."""

    risk: _RiskFinding
    trust: _TrustFinding
    behavior: _BehaviorFinding
    policy: _PolicyFinding
    tool: _ToolFinding
    all_reasons: list[ReasonCode]
    composite_severity: DecisionSeverity
    confidence: float


# ============================================================================
# Public output model
# ============================================================================


@dataclass
class DecisionResult:
    """Fully-explainable security decision produced by :class:`DecisionEngine`.

    Every field is populated on every call — there are no ``None`` gaps in a
    normal result.  Callers should never need to inspect internal engine state
    to understand a decision.

    Attributes:
        decision_id: Unique UUID for this decision (useful for audit logs and
            correlation across distributed services).
        decision: The :class:`Decision` outcome for this request.
        confidence: How certain the engine is, ``[0.0, 1.0]``.  Derived from
            the number of threat matches, trust stability, and evidence
            consistency — independently of ``risk_score``.
        severity: The worst :class:`DecisionSeverity` level observed across
            all sub-evaluators.
        reasoning: Ordered list of machine-readable :class:`ReasonCode` values.
            Empty only for a fully clean ``ALLOW`` decision.
        recommendation: A :class:`Recommendation` describing the suggested
            human or automated response.
        explanation: A single, concise human-readable sentence explaining the
            decision.  Designed for dashboards, alert emails, and audit trails.
        risk_score: Aggregate risk from the Detection Engine (``[0.0, 1.0]``).
        trust_score: Agent's composite trust score at decision time.
        behavior_score: Agent's behavioural sub-score at decision time.
        policy_score: Agent's policy-compliance sub-score at decision time.
        timestamp: UTC timestamp when this decision was produced.

    Example::

        result = engine.decide(det_result, trust_profile, "shell_exec")
        print(result.decision)      # Decision.BLOCK
        print(result.explanation)   # "The message contains ..."
        print(result.reasoning)     # [ReasonCode.COMMAND_INJECTION, ...]
    """

    decision_id: str
    decision: Decision
    confidence: float
    severity: DecisionSeverity
    reasoning: list[ReasonCode]
    recommendation: Recommendation
    explanation: str
    risk_score: float
    trust_score: float
    behavior_score: float
    policy_score: float
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============================================================================
# Decision Intelligence Engine
# ============================================================================


class DecisionEngine:
    """Explainable security decision engine for AgentShield.

    The engine is a **stateless aggregator**: it holds no mutable agent state
    itself.  All state lives in the upstream :class:`~app.core.models.DetectionResult`
    and :class:`~app.core.trust_engine.AgentTrustProfile` objects passed to
    :meth:`decide`.

    Thread safety
    -------------
    All public methods are thread-safe.  A :class:`threading.RLock` protects
    the internal decision counter used for telemetry.

    Singleton usage
    ---------------
    Instantiate once at application startup and share across all request
    handlers::

        decision_engine = DecisionEngine()  # in main.py / DI container

    Custom tool policy
    ------------------
    To override the default unauthorized / sensitive tool lists, pass them at
    construction time::

        engine = DecisionEngine(
            unauthorized_tools={"custom_tool_a"},
            sensitive_tools={"custom_tool_b"},
        )

    Example::

        engine = DecisionEngine()
        result = engine.decide(detection_result, trust_profile, "code_eval")
        assert isinstance(result, DecisionResult)
    """

    def __init__(
        self,
        unauthorized_tools: Optional[frozenset[str]] = None,
        sensitive_tools: Optional[frozenset[str]] = None,
    ) -> None:
        """Initialise the Decision Engine.

        Args:
            unauthorized_tools: Optional override for the set of tool names
                that are unconditionally denied.  Defaults to
                :data:`_UNAUTHORIZED_TOOLS`.
            sensitive_tools: Optional override for the set of tool names that
                are allowed but trigger heightened scrutiny.  Defaults to
                :data:`_SENSITIVE_TOOLS`.
        """
        self._unauthorized_tools: frozenset[str] = (
            unauthorized_tools if unauthorized_tools is not None else _UNAUTHORIZED_TOOLS
        )
        self._sensitive_tools: frozenset[str] = (
            sensitive_tools if sensitive_tools is not None else _SENSITIVE_TOOLS
        )
        self._lock: threading.RLock = threading.RLock()
        # TODO [HISTORY]: Replace this counter with a persistent decision log.
        self._decision_count: int = 0

    # =========================================================================
    # Public API
    # =========================================================================

    def decide(
        self,
        detection_result: DetectionResult,
        trust_profile: AgentTrustProfile,
        requested_tool: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> DecisionResult:
        """Produce a fully-explainable security decision.

        This is the sole public entry point.  It orchestrates all sub-evaluators
        and always returns a complete :class:`DecisionResult` — never raises
        an exception in normal operation.

        Args:
            detection_result: Output of
                :meth:`~app.core.detector.DetectionEngine.analyze`.
            trust_profile: The agent's current
                :class:`~app.core.trust_engine.AgentTrustProfile`.
            requested_tool: Optional name of the capability the agent is
                requesting (e.g. ``"shell_exec"``).  ``None`` means the
                request is not tool-specific.
            context: Optional arbitrary key-value context (session ID,
                geographic region, model version, etc.).  Currently passed
                through to extension points but not used in core logic.

        Returns:
            :class:`DecisionResult` with every field populated.

        Example::

            result = engine.decide(det, profile, "file_read")
            print(result.decision, result.explanation)
        """
        # TODO [THREAT_INTEL]: Enrich detection_result with live threat intel
        #                       feeds before evaluating (e.g. IP reputation,
        #                       known-bad pattern library updates).

        # TODO [GRAPH]: Query a graph correlation layer to check whether this
        #               agent is part of a coordinated attack cluster.

        findings = self._merge_findings(
            risk=self._evaluate_risk(detection_result),
            trust=self._evaluate_trust(trust_profile),
            behavior=self._evaluate_behavior(trust_profile),
            policy=self._evaluate_policy(trust_profile),
            tool=self._evaluate_tool(requested_tool, context),
        )

        result = self._finalize_decision(
            findings=findings,
            detection_result=detection_result,
            trust_profile=trust_profile,
        )

        with self._lock:
            self._decision_count += 1

        # TODO [HISTORY]: Persist result to a decision log / audit store here.

        return result

    @property
    def decision_count(self) -> int:
        """Total number of decisions produced since instantiation.

        Returns:
            int: Decision count (thread-safe read).
        """
        with self._lock:
            return self._decision_count

    # =========================================================================
    # Sub-evaluators — each assesses one dimension of the security signal
    # =========================================================================

    def _evaluate_risk(self, detection_result: DetectionResult) -> _RiskFinding:
        """Evaluate raw threat detection risk.

        Translates :class:`~app.core.models.DetectionResult` into reason codes
        and a peak severity.  Each unique threat *category* contributes at most
        one reason code to avoid duplication.

        Args:
            detection_result: Output of the Detection Engine.

        Returns:
            :class:`_RiskFinding` summarising risk-related signals.
        """
        reasons: list[ReasonCode] = []
        seen_categories: set[str] = set()
        peak_severity = DecisionSeverity.INFO

        for threat in detection_result.threats:
            category = threat.rule.category
            if category not in seen_categories:
                seen_categories.add(category)
                reason = _CATEGORY_TO_REASON.get(category)
                if reason is not None:
                    reasons.append(reason)

            # Track the worst severity seen.
            mapped = _SEVERITY_MAP.get(threat.rule.severity, DecisionSeverity.LOW)
            if _severity_rank(mapped) > _severity_rank(peak_severity):
                peak_severity = mapped

        # TODO [MITRE]: Annotate each reason code with a MITRE ATT&CK technique.

        return _RiskFinding(
            risk_score=detection_result.risk_score,
            reasons=reasons,
            peak_severity=peak_severity,
            threat_count=detection_result.threat_count,
        )

    @staticmethod
    def _evaluate_trust(trust_profile: AgentTrustProfile) -> _TrustFinding:
        """Evaluate agent trust signal.

        Examines the agent's composite trust score, lifecycle status, and
        recent trend to determine trust-related reason codes.

        Args:
            trust_profile: Agent's current trust profile.

        Returns:
            :class:`_TrustFinding` summarising trust-related signals.
        """
        reasons: list[ReasonCode] = []
        is_blocked = trust_profile.status == TrustStatus.BLOCKED
        is_quarantined = trust_profile.status == TrustStatus.QUARANTINED
        is_declining = trust_profile.trend == TrustTrend.DECLINING

        if trust_profile.status == TrustStatus.NEW:
            reasons.append(ReasonCode.UNKNOWN_AGENT)
        if is_blocked:
            reasons.append(ReasonCode.BLOCKED_AGENT)
        if is_quarantined:
            reasons.append(ReasonCode.QUARANTINED_AGENT)
        if trust_profile.trust_score < _TRUST_CRITICAL_THRESHOLD:
            reasons.append(ReasonCode.CRITICAL_TRUST)
        elif trust_profile.trust_score < _TRUST_WARN_THRESHOLD:
            reasons.append(ReasonCode.LOW_TRUST)
        if is_declining:
            reasons.append(ReasonCode.DECLINING_TRUST)

        return _TrustFinding(
            trust_score=trust_profile.trust_score,
            reasons=reasons,
            is_blocked_agent=is_blocked,
            is_quarantined_agent=is_quarantined,
            is_declining=is_declining,
        )

    @staticmethod
    def _evaluate_behavior(trust_profile: AgentTrustProfile) -> _BehaviorFinding:
        """Evaluate the agent's behavioural sub-score.

        A low behavior score indicates the agent has a poor success-rate
        history, suggesting unreliable or anomalous activity.

        Args:
            trust_profile: Agent's current trust profile.

        Returns:
            :class:`_BehaviorFinding` summarising behaviour-related signals.

        Note:
            TODO [FINGERPRINT]: Compare behavior_score against a per-agent
            baseline fingerprint to detect sudden deviations that a raw
            threshold would miss.
        """
        reasons: list[ReasonCode] = []
        if trust_profile.behavior_score < _BEHAVIOR_DEVIATION_THRESHOLD:
            reasons.append(ReasonCode.BEHAVIOR_DEVIATION)
        return _BehaviorFinding(
            behavior_score=trust_profile.behavior_score,
            reasons=reasons,
        )

    @staticmethod
    def _evaluate_policy(trust_profile: AgentTrustProfile) -> _PolicyFinding:
        """Evaluate the agent's policy-compliance sub-score.

        A low policy score indicates a high ratio of blocked or suspicious
        interactions in the agent's history.

        Args:
            trust_profile: Agent's current trust profile.

        Returns:
            :class:`_PolicyFinding` summarising policy-related signals.
        """
        reasons: list[ReasonCode] = []
        if trust_profile.policy_score < _POLICY_VIOLATION_THRESHOLD:
            reasons.append(ReasonCode.POLICY_VIOLATION)
        return _PolicyFinding(
            policy_score=trust_profile.policy_score,
            reasons=reasons,
        )

    def _evaluate_tool(self, requested_tool: Optional[str], context: Optional[dict[str, Any]] = None) -> _ToolFinding:
        """Evaluate whether the requested tool is authorized.

        Args:
            requested_tool: The capability name requested by the agent, or
                ``None`` if the request is not tool-specific.
            context: Optional evaluation context containing interceptor findings.

        Returns:
            :class:`_ToolFinding` summarising tool-authorization signals.
        """
        reasons: list[ReasonCode] = []
        is_unauthorized = False

        if context:
            if context.get("auth_matrix_authorized") is False:
                reasons.append(ReasonCode.UNAUTHORIZED_TOOL_ACCESS)
                is_unauthorized = True
            elif context.get("identity_spoofed") is True:
                reasons.append(ReasonCode.UNAUTHORIZED_TOOL)
                is_unauthorized = True
            
            # Map interceptor telemetry findings to appropriate reason codes
            interceptor_findings = context.get("interceptor_findings", [])
            for finding in interceptor_findings:
                if "Data Exfiltration" in finding:
                    reasons.append(ReasonCode.NETWORK_EXFILTRATION)
                    is_unauthorized = True
                elif "Recursive Tool Loop" in finding:
                    reasons.append(ReasonCode.POLICY_VIOLATION)
                    is_unauthorized = True
                elif "Indirect Prompt Injection" in finding:
                    reasons.append(ReasonCode.PROMPT_INJECTION)
                    is_unauthorized = True

        if requested_tool is not None:
            tool_lower = requested_tool.lower()
            if tool_lower in self._unauthorized_tools:
                reasons.append(ReasonCode.UNAUTHORIZED_TOOL)
                is_unauthorized = True
            elif tool_lower in self._sensitive_tools:
                reasons.append(ReasonCode.SENSITIVE_TOOL)

        return _ToolFinding(
            requested_tool=requested_tool,
            reasons=reasons,
            is_unauthorized=is_unauthorized,
        )

    # =========================================================================
    # Merge & Finalize
    # =========================================================================

    @staticmethod
    def _merge_findings(
        risk: _RiskFinding,
        trust: _TrustFinding,
        behavior: _BehaviorFinding,
        policy: _PolicyFinding,
        tool: _ToolFinding,
    ) -> _MergedFindings:
        """Combine all sub-evaluator outputs into a single coherent picture.

        Deduplicates reason codes, determines the composite severity (the
        worst across all evaluators), and calculates confidence.

        Args:
            risk: Output of :meth:`_evaluate_risk`.
            trust: Output of :meth:`_evaluate_trust`.
            behavior: Output of :meth:`_evaluate_behavior`.
            policy: Output of :meth:`_evaluate_policy`.
            tool: Output of :meth:`_evaluate_tool`.

        Returns:
            :class:`_MergedFindings` ready for :meth:`_finalize_decision`.
        """
        # Deduplicate while preserving insertion order (risk reasons first).
        seen: set[ReasonCode] = set()
        all_reasons: list[ReasonCode] = []
        for reason in (
            risk.reasons
            + trust.reasons
            + behavior.reasons
            + policy.reasons
            + tool.reasons
        ):
            if reason not in seen:
                seen.add(reason)
                all_reasons.append(reason)

        if not all_reasons:
            all_reasons.append(ReasonCode.CLEAN)

        # Composite severity: worst across risk, trust status, and tool authorization.
        trust_severity = _trust_to_severity(trust)
        tool_severity = DecisionSeverity.HIGH if tool.is_unauthorized else DecisionSeverity.INFO
        composite_severity = _max_severity(risk.peak_severity, trust_severity)
        composite_severity = _max_severity(composite_severity, tool_severity)

        confidence = DecisionEngine._calculate_confidence(
            risk=risk,
            trust=trust,
        )

        return _MergedFindings(
            risk=risk,
            trust=trust,
            behavior=behavior,
            policy=policy,
            tool=tool,
            all_reasons=all_reasons,
            composite_severity=composite_severity,
            confidence=confidence,
        )

    @staticmethod
    def _finalize_decision(
        findings: _MergedFindings,
        detection_result: DetectionResult,
        trust_profile: AgentTrustProfile,
    ) -> DecisionResult:
        """Determine the final :class:`Decision` and build the :class:`DecisionResult`.

        Decision priority (first matching condition wins):

        1. Agent is BLOCKED → BLOCK.
        2. Unauthorized tool requested → BLOCK.
        3. Critical risk score → BLOCK.
        4. Agent is QUARANTINED → QUARANTINE.
        5. High risk score → REVIEW.
        6. Agent is SUSPICIOUS, or declining trust + elevated risk → REVIEW.
        7. Moderate risk, or sensitive tool, or low trust → MONITOR.
        8. Minor risk or warning signals → ALLOW_WITH_WARNING.
        9. No signals → ALLOW.

        Args:
            findings: Merged output from all sub-evaluators.
            detection_result: Original Detection Engine output.
            trust_profile: Agent's current trust profile.

        Returns:
            Fully-populated :class:`DecisionResult`.
        """
        decision = DecisionEngine._apply_decision_rules(findings)
        recommendation = _DECISION_TO_RECOMMENDATION[decision]

        # Override recommendation for specific high-severity scenarios.
        if (
            decision in (Decision.BLOCK, Decision.QUARANTINE)
            and findings.trust.is_declining
        ):
            recommendation = Recommendation.INVESTIGATE_AGENT
        elif decision == Decision.BLOCK and findings.trust.is_blocked_agent:
            recommendation = Recommendation.ROTATE_CREDENTIALS

        explanation = DecisionEngine._build_explanation(
            findings=findings,
            decision=decision,
        )

        return DecisionResult(
            decision_id=str(uuid.uuid4()),
            decision=decision,
            confidence=findings.confidence,
            severity=findings.composite_severity,
            reasoning=findings.all_reasons,
            recommendation=recommendation,
            explanation=explanation,
            risk_score=detection_result.risk_score,
            trust_score=trust_profile.trust_score,
            behavior_score=trust_profile.behavior_score,
            policy_score=trust_profile.policy_score,
        )

    @staticmethod
    def _apply_decision_rules(findings: _MergedFindings) -> Decision:
        """Map merged findings to a :class:`Decision` via an ordered rule table.

        Rules are evaluated top-to-bottom; the first match wins.  This
        structure is intentionally a flat sequence of named conditions rather
        than a single compound if-else block so that individual rules can be
        added, removed, or re-ordered in isolation.

        Args:
            findings: Merged sub-evaluator output.

        Returns:
            :class:`Decision` outcome.

        Note:
            TODO [POLICY]: Load this rule table from an external policy plugin
            (e.g. OPA Rego, Cedar policy language) to allow runtime updates
            without code deployment.

            TODO [LLM]: For borderline cases (e.g. MONITOR vs REVIEW), feed the
            full findings context into an LLM reasoning step to produce a
            more nuanced final decision.
        """
        risk = findings.risk
        trust = findings.trust
        tool = findings.tool

        # ── Rule 1: Blocked agent → always block ─────────────────────────────
        if trust.is_blocked_agent:
            return Decision.BLOCK

        # ── Rule 2: Unauthorized tool → always block ──────────────────────────
        if tool.is_unauthorized:
            return Decision.BLOCK

        # ── Rule 3: Critical risk score → block ───────────────────────────────
        if risk.risk_score >= _RISK_BLOCK_THRESHOLD:
            return Decision.BLOCK

        # ── Rule 4: Quarantined agent → quarantine the request ────────────────
        if trust.is_quarantined_agent:
            return Decision.QUARANTINE

        # ── Rule 5: High risk → escalate for human review ─────────────────────
        if risk.risk_score >= _RISK_REVIEW_THRESHOLD:
            return Decision.REVIEW

        # ── Rule 6: Suspicious agent or declining trust + notable risk ────────
        if (
            findings.trust.trust_score < _TRUST_CRITICAL_THRESHOLD
            or (
                trust.is_declining
                and risk.risk_score >= _RISK_WARN_THRESHOLD
            )
        ):
            return Decision.REVIEW

        # ── Rule 7: Moderate risk, sensitive tool, low trust → monitor ────────
        if (
            risk.risk_score >= _RISK_MONITOR_THRESHOLD
            or ReasonCode.SENSITIVE_TOOL in findings.all_reasons
            or ReasonCode.LOW_TRUST in findings.all_reasons
            or ReasonCode.BEHAVIOR_DEVIATION in findings.all_reasons
            or ReasonCode.POLICY_VIOLATION in findings.all_reasons
        ):
            return Decision.MONITOR

        # ── Rule 8: Any warning signals → allow with advisory ─────────────────
        if (
            risk.risk_score >= _RISK_WARN_THRESHOLD
            or ReasonCode.UNKNOWN_AGENT in findings.all_reasons
            or ReasonCode.DECLINING_TRUST in findings.all_reasons
        ):
            return Decision.ALLOW_WITH_WARNING

        # ── Rule 9: No threat signals → allow ────────────────────────────────
        return Decision.ALLOW

    @staticmethod
    def _calculate_confidence(
        risk: _RiskFinding,
        trust: _TrustFinding,
    ) -> float:
        """Calculate decision confidence independently of risk score.

        Confidence reflects *how certain* the engine is about its decision,
        not *how dangerous* the request is.  It is derived from:

        * **Threat count**: More matching patterns → higher confidence.
        * **Trust stability**: A non-declining agent with a known history →
          higher confidence.
        * **Evidence consistency**: Risk and trust signals pointing in the
          same direction → higher confidence.

        Formula::

            confidence = W_THREATS    × threat_signal
                       + W_STABILITY  × stability_signal
                       + W_CONSISTENCY × consistency_signal

        Args:
            risk: Risk sub-evaluator output.
            trust: Trust sub-evaluator output.

        Returns:
            float: Confidence score in ``[0.0, 1.0]``.
        """
        # Signal 1: How many distinct threats were matched (saturates quickly).
        threat_signal = min(
            risk.threat_count / _CONFIDENCE_MAX_THREAT_COUNT, 1.0
        )

        # Signal 2: Trust stability (declining agent → lower confidence).
        stability_signal = 0.0 if trust.is_declining else 1.0
        # Agents with a history of violations reduce our certainty further.
        if ReasonCode.CRITICAL_TRUST in trust.reasons:
            stability_signal *= 0.5
        elif ReasonCode.LOW_TRUST in trust.reasons:
            stability_signal *= 0.75

        # Signal 3: Consistency between risk and trust signals.
        #   Both indicate danger → high consistency.
        #   Only one signals danger → moderate consistency.
        #   Neither signals danger → moderate consistency (clean case).
        risk_flagged = risk.risk_score >= _RISK_WARN_THRESHOLD
        trust_flagged = (
            trust.trust_score < _TRUST_WARN_THRESHOLD
            or trust.is_blocked_agent
            or trust.is_quarantined_agent
        )
        if risk_flagged == trust_flagged:
            consistency_signal = 1.0  # Both agree (either both clean or both dirty).
        else:
            consistency_signal = 0.5  # Mixed signals → moderate certainty.

        confidence = (
            _CONFIDENCE_WEIGHT_THREATS * threat_signal
            + _CONFIDENCE_WEIGHT_TRUST_STABILITY * stability_signal
            + _CONFIDENCE_WEIGHT_CONSISTENCY * consistency_signal
        )
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _build_explanation(
        findings: _MergedFindings,
        decision: Decision,
    ) -> str:
        """Compose a single, concise human-readable explanation sentence.

        The sentence is assembled from up to three phrase fragments:

        1. A detection phrase (what threat patterns were found).
        2. A trust phrase (agent's current reputation state).
        3. A tool phrase (if a sensitive or unauthorized tool was requested).

        Args:
            findings: Merged sub-evaluator output.
            decision: The final :class:`Decision` that was reached.

        Returns:
            str: A single sentence suitable for dashboards and alert emails.

        Note:
            TODO [LLM]: Replace this template approach with an LLM call for
            richer, context-aware explanations that can reference specific
            threat patterns by name and cite historical behaviour.
        """
        fragments: list[str] = []

        # ── Detection fragment ─────────────────────────────────────────────
        detection_reasons = [
            r for r in findings.all_reasons
            if r in (
                ReasonCode.COMMAND_INJECTION,
                ReasonCode.PROMPT_INJECTION,
                ReasonCode.SQL_INJECTION,
                ReasonCode.PATH_TRAVERSAL,
                ReasonCode.CODE_EXECUTION,
                ReasonCode.NETWORK_EXFILTRATION,
            )
        ]
        if detection_reasons:
            reason_labels = " and ".join(
                r.value.replace("_", " ").lower() for r in detection_reasons[:2]
            )
            fragments.append(f"the message contains {reason_labels} patterns")

        # ── Trust fragment ──────────────────────────────────────────────────
        if ReasonCode.BLOCKED_AGENT in findings.all_reasons:
            fragments.append("the agent has been permanently blocked")
        elif ReasonCode.QUARANTINED_AGENT in findings.all_reasons:
            fragments.append("the agent is under active quarantine")
        elif ReasonCode.CRITICAL_TRUST in findings.all_reasons:
            fragments.append("the agent has a critically low trust score")
        elif ReasonCode.LOW_TRUST in findings.all_reasons:
            trust_suffix = " and a declining reputation" if findings.trust.is_declining else ""
            fragments.append(f"the agent has low trust{trust_suffix}")
        elif ReasonCode.UNKNOWN_AGENT in findings.all_reasons:
            fragments.append("the agent has no established interaction history")
        elif ReasonCode.BEHAVIOR_DEVIATION in findings.all_reasons:
            fragments.append("the agent has exhibited abnormal behaviour")
        elif ReasonCode.POLICY_VIOLATION in findings.all_reasons:
            fragments.append("the agent has a history of policy violations")
        elif ReasonCode.DECLINING_TRUST in findings.all_reasons:
            fragments.append("the agent's trust score is trending downward")

        # ── Tool fragment ──────────────────────────────────────────────────
        if ReasonCode.UNAUTHORIZED_TOOL in findings.all_reasons and findings.tool.requested_tool:
            fragments.append(
                f"the requested capability '{findings.tool.requested_tool}' is not authorized"
            )
        elif ReasonCode.SENSITIVE_TOOL in findings.all_reasons and findings.tool.requested_tool:
            fragments.append(
                f"the requested capability '{findings.tool.requested_tool}' requires elevated scrutiny"
            )

        # ── Assembly ───────────────────────────────────────────────────────
        if not fragments:
            return (
                f"No threat signals detected; request is permitted "
                f"(confidence: {findings.confidence:.0%})."
            )

        # Join fragments grammatically.
        if len(fragments) == 1:
            body = fragments[0].capitalize()
        elif len(fragments) == 2:
            body = f"{fragments[0].capitalize()} while {fragments[1]}"
        else:
            body = (
                f"{fragments[0].capitalize()}, {fragments[1]}, "
                f"and {fragments[2]}"
            )

        action_phrase = _decision_to_action_phrase(decision)
        return f"{body}; {action_phrase}."


# ============================================================================
# Module-level pure helpers
# ============================================================================


def _severity_rank(severity: DecisionSeverity) -> int:
    """Return an integer rank for a :class:`DecisionSeverity` (higher = worse).

    Args:
        severity: The severity level to rank.

    Returns:
        int: Rank in ``[0, 4]``.
    """
    _ranks: dict[DecisionSeverity, int] = {
        DecisionSeverity.INFO: 0,
        DecisionSeverity.LOW: 1,
        DecisionSeverity.MEDIUM: 2,
        DecisionSeverity.HIGH: 3,
        DecisionSeverity.CRITICAL: 4,
    }
    return _ranks.get(severity, 0)


def _max_severity(a: DecisionSeverity, b: DecisionSeverity) -> DecisionSeverity:
    """Return the higher of two :class:`DecisionSeverity` values.

    Args:
        a: First severity.
        b: Second severity.

    Returns:
        Whichever of *a* or *b* has the greater rank.
    """
    return a if _severity_rank(a) >= _severity_rank(b) else b


def _trust_to_severity(trust: _TrustFinding) -> DecisionSeverity:
    """Map a :class:`_TrustFinding` to the corresponding :class:`DecisionSeverity`.

    Args:
        trust: Trust sub-evaluator output.

    Returns:
        :class:`DecisionSeverity` reflecting the agent's trust state.
    """
    if trust.is_blocked_agent:
        return DecisionSeverity.CRITICAL
    if trust.is_quarantined_agent:
        return DecisionSeverity.HIGH
    if ReasonCode.CRITICAL_TRUST in trust.reasons:
        return DecisionSeverity.HIGH
    if ReasonCode.LOW_TRUST in trust.reasons:
        return DecisionSeverity.MEDIUM
    if ReasonCode.DECLINING_TRUST in trust.reasons:
        return DecisionSeverity.LOW
    return DecisionSeverity.INFO


def _decision_to_action_phrase(decision: Decision) -> str:
    """Return a short action phrase suitable for the end of an explanation sentence.

    Args:
        decision: The :class:`Decision` outcome.

    Returns:
        str: A lowercase phrase fragment (no trailing punctuation).
    """
    _phrases: dict[Decision, str] = {
        Decision.ALLOW: "request permitted",
        Decision.ALLOW_WITH_WARNING: "request permitted with advisory",
        Decision.MONITOR: "agent placed under monitoring",
        Decision.REVIEW: "request escalated for human review",
        Decision.QUARANTINE: "agent quarantined pending investigation",
        Decision.BLOCK: "request blocked immediately",
    }
    return _phrases.get(decision, "decision recorded")
