# Trust Engine

The Trust Engine maintains dynamic, composite trust scores for every AI agent in the system, enabling reputation-based security decisions.

---

## Purpose

Answer: **"How trustworthy is this agent based on its entire interaction history?"**

The Trust Engine provides the long-term reputation signal that influences whether downstream security decisions are strict or lenient.

---

## Design

### Architecture

```
Event (success/suspicious/block) → Counter Update → Score Recomputation → Profile Update
                                                              ↓
                                            trust_score, security_grade, status, trend
```

### Key Components

| Component | Role |
|-----------|------|
| `AgentTrustProfile` | Complete trust state: scores, counters, grade, status, trend, history |
| `TrustStatus` | Lifecycle enum: NEW, TRUSTED, VERIFIED, MONITOR, SUSPICIOUS, QUARANTINED, BLOCKED |
| `TrustTrend` | Trend enum: IMPROVING, STABLE, DECLINING |

---

## Data Flow

### Event Recording

1. Validate agent ID
2. Get or create the agent's trust profile
3. Increment the appropriate counter (successful, suspicious, or blocked)
4. Run the score update pipeline
5. Persist the updated profile

### Score Update Pipeline

Executed in strict order after every event:

1. **Behavior score** = success rate (with cold-start blending for new agents)
2. **Policy score** = 1.0 - (violation_rate × multiplier)
3. **Composite trust score** = weighted combination of history (40%), behavior (35%), and policy (25%)
4. **Poisoning guard:** Delta-cap applied — max +0.05 increase and max -0.25 decrease per event (unless severe block)
5. Push score to history ring buffer
6. Derive security grade (A+ through F)
7. Derive lifecycle status from score thresholds
8. Compute trend from ring buffer (oldest vs newest)

---

## Key Algorithms

### Composite Trust Formula

```
trust = 0.40 × history_score + 0.35 × behavior_score + 0.25 × policy_score
```

- **History** provides momentum/inertia — prevents wild score swings
- **Behavior** reflects the agent's success rate
- **Policy** penalizes violations with an amplification multiplier

### Trust Poisoning Rate Limiting

An attacker who sends many clean requests to inflate their trust score before launching an attack is performing a **trust farming attack**. The delta cap mitigates this:

- Positive delta capped at **+0.05** per event
- Negative delta capped at **-0.25** per event (unless `policy_score < 0.20`, allowing immediate drops for severe threats)

This means an attacker needs at least 3 clean events to gain +0.15 trust, but a single block can cost -0.25.

### Score Thresholds

| Score Range | Status | Grade |
|-------------|--------|-------|
| ≥ 0.95 | TRUSTED | A+ |
| ≥ 0.85 | VERIFIED | A |
| ≥ 0.75 | VERIFIED | B |
| ≥ 0.55 | MONITOR | C |
| ≥ 0.30 | SUSPICIOUS | D |
| ≥ 0.10 | QUARANTINED | F |
| < 0.10 | BLOCKED | F |

### Trend Detection

A ring buffer of the last 10 score snapshots. The trend is:
- **IMPROVING** if `newest - oldest > 0.04`
- **DECLINING** if `newest - oldest < -0.04`
- **STABLE** otherwise

---

## Extension Points

- **Time decay:** Multiply history score by a decay coefficient so inactive agents drift toward a neutral prior
- **Persistent storage:** Replace in-memory dict with database (ORM upsert or Redis HSET)
- **Audit logging:** Emit structured before/after state for every score change
