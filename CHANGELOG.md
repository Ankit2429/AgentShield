# Changelog

All notable changes to AgentShield will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-12

### Added
- **Detection Engine:** Stateless regex-based threat detection for Prompt Injection, Command Injection, and Data Exfiltration.
- **Behavioral DNA Engine:** Statistical baseline anomaly detection for agents with zero-day threat capabilities.
- **Trust Engine:** Composite reputation scoring (History, Behavior, Policy) with delta-caps to prevent trust farming.
- **Decision Engine:** Centralized rule aggregation emitting deterministic security verdicts (`ALLOW`, `MONITOR`, `BLOCK`, `QUARANTINE`).
- **Replay Engine:** Forensic frame-by-frame serialization of AI interaction lifecycles.
- **Custom JWT Authentication:** Supply-chain secure implementation of HS256 JWTs with PBKDF2 password hashing and active revocation.
- **Role-Based Access Control (RBAC):** Admin, Security Analyst, and Viewer permissions enforced via FastAPI middleware.
- **DevOps Pipeline:** Multi-stage Nginx Dockerfile for the frontend and Gunicorn/Uvicorn non-root configuration for the backend.
- **Comprehensive Test Suite:** 100% core engine line coverage via `pytest`.
- **Documentation Suite:** 12+ files covering architecture, deployment, and security.

### Changed
- Refactored entire backend to use singleton engines via FastAPI dependency injection.
- Replaced development server setup in Docker Compose with robust production emulation (`unless-stopped` policies, postgres/redis stubs).
- Rewrote `README.md` to professional enterprise standards with Mermaid diagrams.

### Removed
- Removed MVP mock files, obsolete ORM models, and empty database migrations.
- Removed legacy `httpx2` dependency in favor of standard `httpx`.
- Stripped all `print()` statements in favor of structured logging.

### Security
- Implemented `RequestSizeLimiterMiddleware` to reject payloads >2MB.
- Implemented `HardeningHeadersMiddleware` for HSTS, CSP, and framing protection.
- Enhanced CORS parsing to support safe multi-origin deployments.
- Excluded malicious payloads from Behavioral DNA baseline training to prevent data poisoning.
