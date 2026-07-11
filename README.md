# AgentShield

AgentShield is a full-stack security and trust monitoring system for multi-agent environments. It intercepts, detects, and monitors communications between agents to protect against malicious behavior, authorization violations, and other attacks.

## Folder Structure

- `backend/`: FastAPI application containing core interception, detection, and trust evaluation modules.
- `frontend/`: React-based dashboard visualizing agent relationships, trust levels, messages, alerts, and audit logs.
- `simulation/`: Simulates different agent interactions and attack scenarios.
- `docs/`: System documentation (Architecture, API, Deployment).
- `docker-compose.yml`: Multi-container orchestration.

## Getting Started

Refer to [docs/DEPLOYMENT.md](file:///d:/antigravity%20projects/agentsheild/docs/DEPLOYMENT.md) for detailed deployment instructions.

### Configuration Management
Before running the application, copy the environment template to create a local `.env` configuration file:
```bash
cp .env.template .env
```
Key parameters include:
- `APP_ENV`: Configure as `development` to expose detailed exception tracebacks, or `production` to hide tracebacks securely.
- `SECRET_KEY`: Set a cryptographic signing string for backend sessions.

> [!NOTE]
> **Settings Architecture:** In the current release version, parameters altered under the "Settings" tab in the user interface are persisted inside browser `localStorage`. System services run with default secure parameters defined in the backend configurations.

