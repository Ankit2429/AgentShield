# Behavioral DNA Engine

The Behavioral DNA Engine builds unique fingerprints for each AI agent and detects anomalous behavior by measuring statistical deviations from established baselines.

---

## Purpose

Answer: **"Is this agent behaving normally compared to its historical pattern?"**

Unlike the Detection Engine (which matches known attack signatures), the DNA Engine detects **zero-day anomalies** — behaviors that have never been seen before and may indicate compromise.

---

## Design

### Architecture

```
Observation → Profile Update → Fingerprint Generation
                                         ↓
New Observation → Deviation Analysis → BehaviorAnalysis (NORMAL/ANOMALOUS/CRITICAL)
```

The engine maintains a per-agent statistical profile that evolves with every interaction.

### Key Components

| Component | Role |
|-----------|------|
| `BehaviorObservation` | Input record: tool, message length, risk score, threat categories |
| `BehaviorProfile` | Accumulated baseline: averages, frequencies, intervals, fingerprint |
| `BehaviorAnalysis` | Output: deviation level, anomaly details, confidence score |
| `DeviationLevel` | Enum: NORMAL, MINOR, MODERATE, SIGNIFICANT, CRITICAL |

---

## Data Flow

### Baseline Training (register_observation)

1. Validate agent ID
2. Get or create the agent's profile
3. **Poisoning guard:** Only update the baseline if `risk_score ≤ 0.30` AND no threat categories are present. Otherwise, increment the request counter but skip statistical updates.
4. Update rolling averages for message length, request interval, and risk score
5. Update tool usage frequency map
6. Recompute the behavioral fingerprint hash

### Anomaly Detection (analyze_behavior)

1. If the agent has fewer than the minimum observations threshold, return NORMAL (benefit-of-the-doubt)
2. Compare the new observation against the profile baseline:
   - **Tool deviation:** Is this tool rarely or never used by this agent?
   - **Length deviation:** Does the message length deviate significantly from the mean?
   - **Interval deviation:** Is the request interval abnormally fast or slow?
   - **Risk deviation:** Is the risk score much higher than this agent's historical average?
3. Combine deviation scores into an overall anomaly level
4. Return `BehaviorAnalysis` with per-dimension breakdowns

---

## Key Algorithms

### Fingerprint Generation

A SHA-256 hash computed from the profile's statistical properties:
- Sorted tool usage frequencies
- Average message length
- Average request interval
- Normal risk score

The fingerprint stabilizes as the profile converges, providing a quick identifier for behavioral state.

### Poisoning Resistance

Observations with `risk_score > 0.30` or containing threat categories are **excluded** from baseline calculations. This prevents an attacker from deliberately shifting the statistical baseline to make future malicious requests appear normal.

### Cold Start

Agents with fewer than the minimum observation threshold receive NORMAL verdicts by default. This prevents false positives during the initial profiling period.

---

## Extension Points

- **Time-series store:** Migrate from in-memory `dict` to InfluxDB/TimescaleDB for persistence and historical queries
- **ML clustering:** Use unsupervised clustering to group agents by behavioral similarity
- **Decay:** Apply time-decay to old observations so the baseline adapts to legitimate behavioral changes
