# Backend

Overview of the AgentShield backend architecture, module organization, and design patterns.

---

## Technology

- **Framework:** FastAPI (async-capable Python web framework)
- **Validation:** Pydantic v2 with strict schemas
- **Server:** Uvicorn (ASGI)
- **Authentication:** Custom HS256 JWT (zero third-party crypto dependencies)

---

## Module Structure

```
backend/app/
├── main.py              # FastAPI app instance, middleware, exception handlers
├── config.py            # Environment configuration with startup validation
├── api/
│   ├── __init__.py      # v1 router assembly
│   ├── deps.py          # Engine singletons + auth dependency providers
│   ├── schemas.py       # All Pydantic request/response models
│   └── routers/
│       ├── analyze.py   # POST /analyze — full pipeline orchestration
│       ├── auth.py      # Authentication (login, refresh, logout, me)
│       ├── agents.py    # GET /agents — trust profile listing
│       ├── dashboard.py # GET /dashboard — operational metrics
│       ├── replay.py    # GET /replay — session listing + timeline
│       ├── health.py    # GET /health — liveness check
│       └── ws.py        # WebSocket real-time event endpoint
├── core/
│   ├── detector.py       # Detection Engine
│   ├── behavior_dna.py   # Behavioral DNA Engine
│   ├── trust_engine.py   # Trust Engine
│   ├── decision_engine.py# Decision Engine
│   ├── replay/           # Replay Engine subsystem
│   ├── events/           # Event bus + lifecycle
│   ├── auth_matrix.py    # Agent capability authorization
│   ├── interceptor.py    # AI threat scanning
│   ├── replay_protector.py # Request deduplication
│   ├── audit_logger.py   # Structured audit logging
│   ├── rules.py          # Detection rule definitions
│   ├── models.py         # Detection data models
│   ├── severity.py       # Severity enumeration
│   └── utils.py          # Text normalization, risk calculation
└── utils/
    └── jwt.py            # JWT signing, verification, revocation
```

---

## Design Patterns

### Singleton Engines
All engines are instantiated once in `deps.py` and injected via FastAPI's `Depends()` system. This provides:
- Single-instance shared state (thread-safe via `RLock`)
- Easy testing (swap the provider function)
- No global imports in routers

### Strict Schema Boundary
Internal engine dataclasses (e.g. `AgentTrustProfile`, `BehaviorAnalysis`) are never exposed directly in API responses. They are always translated to Pydantic schemas in the router layer, keeping the API contract stable across internal refactors.

### Middleware Stack
Requests pass through middleware in this order:
1. `RequestSizeLimiterMiddleware` — Reject payloads > 2MB
2. `HardeningHeadersMiddleware` — Inject security headers
3. `CORSMiddleware` — Origin validation
4. Router-level JWT authentication and RBAC

### Extension Points
All core engines document migration paths via `TODO` comments:
- Storage: In-memory → SQLAlchemy / Redis
- Auth: Static users → External IdP
- Rate limiting: None → token-bucket middleware
- Monitoring: print() → Prometheus / Sentry
