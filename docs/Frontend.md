# Frontend

Overview of the AgentShield frontend — a React-based SOC dashboard for real-time security monitoring.

---

## Technology

- **Framework:** React 18
- **Styling:** Tailwind CSS
- **Data Visualization:** D3.js
- **HTTP Client:** Axios
- **Real-time:** Native WebSocket API

---

## Component Architecture

```
frontend/src/
├── App.js                          # Root — auth state, routing, sidebar
├── index.js                        # React DOM entry point
├── components/
│   ├── DashboardView.js            # Command Overview — live metrics
│   ├── ThreatsView.js              # Threat investigation panels
│   ├── ReplayView.js               # Timeline replay visualization
│   ├── AgentsView.js               # Fleet status — trust profiles
│   ├── SandboxView.js              # Interactive analysis sandbox
│   ├── IncidentIntelligencePanel.js # Incident assessment
│   └── SettingsView.js             # User preferences
├── services/
│   └── api.js                      # API client + token management
└── styles/
    └── (Tailwind configuration)
```

---

## Authentication Flow

1. User enters credentials on the login form
2. `loginUser()` calls `POST /api/v1/auth/login`
3. Access and refresh tokens are stored in `localStorage`
4. All subsequent API calls include the `Authorization: Bearer` header via Axios interceptor
5. On 401 response, the interceptor attempts token refresh via `POST /api/v1/auth/refresh`
6. If refresh fails, the `auth_required` event is dispatched, clearing tokens and returning to the login screen

---

## View Descriptions

| View | Access | Description |
|------|--------|-------------|
| **Command Overview** | All roles | Real-time metrics: active agents, sessions, threats, blocks, trust averages, recent decisions |
| **Threat Investigation** | Admin, Analyst | Detailed threat analysis with matched rules, risk scores, and detection breakdowns |
| **Replay Timeline** | Admin, Analyst | Frame-by-frame forensic replay of security interactions with stage-level detail |
| **Fleet Status** | All roles | Sortable/filterable table of all agent trust profiles with grades and trends |
| **Sandbox** | Admin, Analyst | Manual message analysis tool — submit any message to see how the pipeline evaluates it |
| **Incident Intelligence** | Admin | Aggregated incident views with severity classification |
| **Settings** | All roles | User interface preferences (persisted in `localStorage`) |

---

## Real-time Updates

The dashboard establishes a WebSocket connection to `/api/v1/ws?token=JWT` on mount. The connection receives structured JSON messages for each stage of the analysis pipeline:

```json
{
  "type": "pipeline_progress",
  "stage": "DETECTION",
  "agent_id": "agent-support",
  "session_id": "sess-001",
  "data": { ... }
}
```

This enables live visualization of security decisions as they happen.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single-page architecture** | All views rendered within `App.js` via tab state — no router dependency needed for this scope |
| **localStorage for tokens** | Standard SPA pattern. HttpOnly cookies would require same-origin backend serving. |
| **Tailwind CSS** | Rapid UI development with consistent design tokens |
| **D3.js** | Full control over data visualizations (trust charts, risk gauges) |
