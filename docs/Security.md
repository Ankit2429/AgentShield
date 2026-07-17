# Security Architecture

AgentShield employs defense-in-depth security engineering to protect the platform and the multi-agent systems it monitors.

---

## 1. Application Security

### Authentication
- **Custom JWT:** HS256 (HMAC-SHA256) implementation with standard Python libraries to avoid supply chain vulnerabilities in third-party JWT packages
- **Token Pairing:** Short-lived access tokens (15m) + long-lived refresh tokens (7d)
- **Token Revocation:** Logout invalidates the active refresh token ID (JTI) in an in-memory blacklist
- **Refresh Rotation:** Every refresh invalidates the old token and issues a new pair

### Password Security
- **Algorithm:** PBKDF2 with SHA-256
- **Iterations:** 100,000 rounds
- **Salt:** 16-byte random salt generated securely per-user
- **Constant Time:** Password verification uses `hmac.compare_digest()` to prevent timing side-channel attacks

### Authorization (RBAC)
Three-tier Role-Based Access Control enforced at the router layer via dependency injection:
- **Admin:** Full read/write access
- **Security Analyst:** Access to analysis, replay, dashboard, fleet
- **Viewer:** Read-only access to dashboard and fleet

### Input Validation
- **Schema Strictness:** All Pydantic models use `extra = "forbid"` to reject unknown fields and prevent mass-assignment attacks
- **Payload Limits:** Custom ASGI middleware (`RequestSizeLimiterMiddleware`) drops requests exceeding 2MB before parsing
- **Type Checking:** Strict type enforcement via FastAPI/Pydantic

### Output Protection
- **Security Headers:** HSTS, X-Content-Type-Options, X-Frame-Options injected via middleware
- **Exception Masking:** Detailed tracebacks are scrubbed when `APP_ENV=production`
- **Audit Scrubbing:** The `AuditLogger` automatically redacts passwords, tokens, API keys, and authorization headers before logging

---

## 2. AI Threat Defense

AgentShield includes purpose-built defenses against attacks targeting AI agents.

### Interceptor Guard
- **Indirect Prompt Injection:** Detects XML tag overrides (`<instructions>`) and markdown comment injection
- **Data Exfiltration:** Scans for patterns resembling private keys, credit cards, and cloud API tokens
- **Recursive Tool Loops:** Tracks per-session tool call chains. Blocks execution if the same tool is called consecutively > 3 times, or if the chain exceeds 8 total calls
- **Cross-Agent Contamination:** Warns if an agent attempts to access context explicitly owned by another agent

### Capability Authorization
- **AuthMatrix:** Maps agents to strict tool-permission boundaries
- **Identity Spoofing Guard:** Verifies the agent ID against its claimed role

### Poisoning Resistance
- **Trust Farming Guard:** The Trust Engine caps positive trust score accumulation at `+0.05` per event. It takes multiple clean requests to build trust, but one severe policy violation can immediately drop trust by `-0.25`
- **Behavioral Baseline Guard:** The Behavior DNA engine excludes malicious interactions (`risk_score > 0.30` or containing threat categories) from its statistical baseline, preventing an attacker from normalizing malicious behavior

### Replay Protection
- **Deduplication:** The `ReplayProtector` generates a SHA-256 hash of the request payload combined with the `event_id`
- **Sliding Window:** Duplicate requests within a 10-minute window are rejected with `409 Conflict`

---

## 3. Network & Infrastructure

### REST API
- **CORS:** Controlled via `CORS_ORIGIN_WHITELIST` environment variable in production
- **TLS:** Expected to be terminated at the reverse proxy layer

### WebSocket Layer
- **Authentication:** Validates JWT in the initial connection upgrade request
- **Connection Limits:** Maximum 10 concurrent connections to prevent connection exhaustion
- **Message Limits:** Maximum 64KB per message
- **Idle Pruning:** Background task disconnects idle clients after 60 seconds

### Docker
- **Minimal Surface:** Alpine Linux-based Node container, lightweight Python backend container
- **Non-Root Execution:** Recommended for production deployment (TODO)

---

## 4. Known Hardening Opportunities

While hardened for portfolio deployment, production use at scale should address the following (documented in the Security Audit Report):

- **Rate Limiting:** Implement per-IP rate limiting on `/api/v1/auth/login` to deter credential brute-forcing
- **Unbounded Collections:** Implement TTL-based eviction on the `RevokedTokenRegistry`, `ReplayProtector` dictionary, and `MessageInterceptor` session chains to prevent memory exhaustion under sustained attack
