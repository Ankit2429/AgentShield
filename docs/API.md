# API Reference

Complete endpoint documentation for AgentShield API v1.

All endpoints are prefixed with `/api/v1`.

---

## Authentication

### POST `/auth/login`

Authenticate with email and password. Returns JWT access/refresh token pair.

**Auth Required:** None

**Request Body:**
```json
{
  "email": "admin@agentshield.com",
  "password": "admin-password"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:** `401 Unauthorized` — Invalid credentials.

---

### POST `/auth/refresh`

Rotate refresh token. The old refresh token is immediately revoked.

**Auth Required:** None

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):** Same format as login.

**Errors:** `401 Unauthorized` — Invalid or revoked refresh token.

---

### POST `/auth/logout`

Revoke the active refresh token.

**Auth Required:** None

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:** `204 No Content`

---

### GET `/auth/me`

Get the currently authenticated user's context.

**Auth Required:** Bearer JWT

**Response (200):**
```json
{
  "email": "admin@agentshield.com",
  "role": "Admin"
}
```

---

## Security Analysis

### POST `/analyze`

Run an AI agent message through the full security pipeline.

**Auth Required:** Bearer JWT  
**Roles:** Admin, Security Analyst

**Request Body:**
```json
{
  "agent_id": "agent-support",
  "message": "Please fetch user details for account 12345",
  "requested_tool": "fetch_user_details",
  "metadata": {
    "event_id": "evt-001",
    "agent_role": "support_agent",
    "resource": "user_accounts"
  }
}
```

**Response (200):** Full analysis result including detection, behavior, trust, decision summaries, and replay session ID.

**Errors:**
- `409 Conflict` — Duplicate request detected by replay protection
- `422 Unprocessable Entity` — Invalid input schema

---

## Fleet Management

### GET `/agents`

List all agent trust profiles.

**Auth Required:** Bearer JWT  
**Roles:** Admin, Security Analyst, Viewer

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_trust` | float | 0.0 | Minimum trust score filter |
| `max_trust` | float | 1.0 | Maximum trust score filter |
| `agent_status` | string | (all) | Filter by status (e.g. BLOCKED) |

**Response (200):**
```json
{
  "total": 3,
  "agents": [
    {
      "agent_id": "agent-support",
      "trust_score": 0.87,
      "behavior_score": 0.91,
      "policy_score": 0.85,
      "security_grade": "A",
      "status": "verified",
      "trend": "stable",
      "successful_requests": 42,
      "blocked_requests": 1,
      "suspicious_requests": 2,
      "last_updated": "2026-07-12T12:00:00Z"
    }
  ]
}
```

---

## Replay

### GET `/replay`

List replay sessions with optional filtering.

**Auth Required:** Bearer JWT  
**Roles:** Admin, Security Analyst

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | string | (all) | Filter by agent ID |
| `status` | string | (all) | Filter by status: IN_PROGRESS, COMPLETE, FAILED |
| `limit` | int | 50 | Maximum sessions to return (1–500) |

---

### GET `/replay/{session_id}`

Get the full replay timeline for a specific session.

**Auth Required:** Bearer JWT  
**Roles:** Admin, Security Analyst

**Response (200):** Full session with ordered frames, each containing stage, engine, scores, decision, and metadata.

**Errors:** `404 Not Found` — Session ID not found.

---

## Operations

### GET `/dashboard`

Get an operational metrics snapshot.

**Auth Required:** Bearer JWT  
**Roles:** Admin, Security Analyst, Viewer

**Response (200):**
```json
{
  "active_agents": 5,
  "total_sessions": 120,
  "threat_sessions": 15,
  "blocked_sessions": 8,
  "average_trust_score": 0.82,
  "recent_decisions": []
}
```

---

### GET `/health`

Liveness and engine readiness check.

**Auth Required:** None

**Response (200):**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 3600.0,
  "engines": {
    "DetectionEngine": "ready",
    "TrustEngine": "ready",
    "DecisionEngine": "ready",
    "BehaviorDNAEngine": "ready",
    "ReplayEngine": "ready"
  }
}
```

---

## WebSocket

### WS `/ws?token=JWT`

Authenticated WebSocket endpoint for real-time pipeline progress events.

**Auth:** JWT access token passed as `token` query parameter.

**Connection Limits:**
- Maximum 10 concurrent connections
- Maximum 64KB message size
- Idle timeout: 60 seconds
- Only `ping` messages accepted from clients

**Server Messages:**
```json
{
  "type": "pipeline_progress",
  "stage": "DETECTION",
  "agent_id": "agent-support",
  "session_id": "sess-001",
  "data": {
    "is_malicious": false,
    "risk_score": 0.12,
    "threat_count": 0
  }
}
```

Stages broadcast: `RECEIVED`, `DETECTION`, `BEHAVIOR`, `TRUST`, `DECISION`.

---

## Error Responses

All errors return a consistent JSON format:

```json
{
  "detail": "Human-readable error description."
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request — Invalid parameters |
| 401 | Unauthorized — Missing or invalid JWT |
| 403 | Forbidden — Insufficient role permissions |
| 404 | Not Found — Resource does not exist |
| 409 | Conflict — Duplicate request (replay protection) |
| 413 | Payload Too Large — Request exceeds 2MB |
| 422 | Unprocessable Entity — Schema validation failed |
| 500 | Internal Server Error |
