# Decision Engine

The Decision Engine is the final arbiter of the AgentShield X security pipeline. It synthesizes signals from all upstream engines into an explainable security verdict.

---

## Purpose

Answer: **"Should this agent interaction be allowed, monitored, blocked, or quarantined — and why?"**

---

## Design

### Architecture

```
DetectionResult + BehaviorAnalysis + TrustProfile + Context → Rule Evaluation → DecisionResult
                                                                                       ↓
                                                              Decision + Severity + Reasons + Recommendations
```

### Key Components

| Component | Role |
|-----------|------|
| `Decision` | Enum: ALLOW, MONITOR, BLOCK, QUARANTINE |
| `DecisionSeverity` | Enum: NONE, LOW, MEDIUM, HIGH, CRITICAL |
| `ReasonCode` | Standardized reason identifiers for each decision factor |
| `Recommendation` | Actionable response suggestions |
| `DecisionResult` | Complete verdict with reasoning chain |

---

## Data Flow

1. **Receive inputs:** Detection result, behavioral analysis, trust profile, and optional context parameters (interceptor findings, auth matrix results)
2. **Evaluate rules:** Each rule examines a specific signal:
   - Risk score thresholds
   - Threat severity levels
   - Behavioral deviation magnitude
   - Trust score ranges
   - Trust trend direction
   - Tool authorization status
   - Interceptor findings (injection, exfiltration, loops)
   - Identity spoofing flags
3. **Aggregate:** Collect all triggered rules, take the most severe decision
4. **Explain:** Build a reasoning chain with:
   - Primary decision and severity
   - All contributing reason codes
   - Confidence score
   - Recommended response actions
5. **Return:** `DecisionResult` with full audit trail

---

## Key Algorithms

### Rule Priority

Rules are evaluated in severity order. The final decision is the **most restrictive** verdict from all triggered rules:

```
QUARANTINE > BLOCK > MONITOR > ALLOW
```

### Explainability

Every `DecisionResult` includes:
- **Reason codes:** Machine-readable identifiers (e.g. `HIGH_RISK_SCORE`, `BEHAVIORAL_ANOMALY`, `LOW_TRUST`)
- **Descriptions:** Human-readable explanations for each contributing factor
- **Confidence:** How strongly the engine believes in the decision (0.0–1.0)
- **Recommendations:** Actionable next steps (e.g. "Quarantine agent for manual review")

### Context Integration

The Decision Engine accepts `context_params` from the analyze router, which include:
- `identity_spoofed`: Boolean from AuthMatrix verification
- `auth_matrix_authorized`: Boolean from capability check
- `interceptor_findings`: List of strings from MessageInterceptor

These are evaluated as additional rule inputs, allowing AI-specific threat signals to influence the decision.

---

## Extension Points

- **Custom rules:** Add domain-specific rules without modifying the engine core
- **ML classifier:** Replace or augment rule-based decisions with a trained model
- **Policy plugins:** Integrate with Open Policy Agent (OPA) or Cedar for externalized policy management
- **Webhooks:** Dispatch notifications on BLOCK/QUARANTINE decisions
