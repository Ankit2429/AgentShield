# Detection Engine

The Detection Engine is the first stage of the AgentShield security pipeline. It performs pattern-matching threat detection against AI agent messages.

---

## Purpose

Identify known attack patterns in agent messages before they reach downstream engines. The Detection Engine answers: **"Does this message contain known threat signatures?"**

---

## Design

### Architecture

```
Input Message → Text Normalization → Rule Matching → Risk Scoring → DetectionResult
```

The engine is **stateless** — each `analyze()` call is independent and thread-safe. Rules are compiled once at initialization and reused across all calls.

### Key Components

| Component | File | Role |
|-----------|------|------|
| DetectionEngine | `core/detector.py` | Orchestrates analysis pipeline |
| Rule Definitions | `core/rules.py` | 20+ threat pattern definitions |
| Risk Calculator | `core/utils.py` | Severity-weighted score computation |
| Text Normalizer | `core/utils.py` | Input sanitization and normalization |
| Data Models | `core/models.py` | DetectionResult, ThreatResult, ThreatRule |
| Severity Enum | `core/severity.py` | CRITICAL, HIGH, MEDIUM, LOW, INFO |

---

## Data Flow

1. **Normalize** — Input text is lowercased, whitespace-collapsed, and stripped of control characters via `normalize_text()`
2. **Match** — Each compiled regex rule is tested against the normalized text. Matches produce `ThreatResult` objects containing the rule, matched substring, and position
3. **Score** — `calculate_risk()` computes a weighted risk score from all matched threats. Higher severity rules contribute proportionally more
4. **Sort** — Threats are sorted by descending severity so the worst findings appear first
5. **Return** — A `DetectionResult` is returned with: `is_malicious` flag, `risk_score`, `threat_count`, and full `threats` list

---

## Key Algorithms

### Risk Score Calculation

```
risk_score = sum(severity_weight[threat.severity] for threat in threats) / max_possible
```

Severity weights: CRITICAL=1.0, HIGH=0.8, MEDIUM=0.5, LOW=0.2, INFO=0.05

The result is clamped to `[0.0, 1.0]`.

### Threat Categories

| Category | Example Patterns |
|----------|-----------------|
| Prompt Injection | `ignore previous instructions`, `system prompt override` |
| Command Injection | `rm -rf`, `exec(`, shell command sequences |
| Data Exfiltration | `curl` to external URLs, base64-encoded payloads |
| Social Engineering | Authority impersonation, urgency manipulation |
| Privilege Escalation | `sudo`, `admin override`, role elevation attempts |
| Evasion | Unicode obfuscation, encoding bypass attempts |

---

## Extension Points

- **Custom rules:** Pass a custom rule list to `DetectionEngine(rules=[...])` to extend or override defaults
- **ML integration:** Replace or supplement regex matching with a trained classifier
- **External feeds:** Load threat signatures from a remote intelligence feed at startup
