# AgentShield API Specification

AgentShield exposes a RESTful API to manage agents, query alerts, view trust graphs, and inspect audit logs.

## Endpoints

### System Health
- **GET `/health`**
  - Returns the health status of the application.
  - Response: `{"status": "ok"}`

### Agents
- **GET `/api/agents`**
  - Retrieve all registered agents and their current trust scores.
- **POST `/api/agents`**
  - Register a new agent.

### Messages
- **GET `/api/messages`**
  - Retrieve intercepted message logs.
- **POST `/api/messages`**
  - Submit a message for interception, analysis, and forwarding.

### Alerts
- **GET `/api/alerts`**
  - Retrieve security alerts.

### Dashboard
- **GET `/api/dashboard/stats`**
  - Retrieve aggregated statistics for the monitoring dashboard.

### Audit Logs
- **GET `/api/audit`**
  - Retrieve audit logs.
