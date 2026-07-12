# Vercel Deployment Guide (Frontend)

AgentShield X uses a React single-page application built with Create React App (CRA). Vercel is the optimal platform for this deployment.

## Vercel Project Configuration

When importing the repository into Vercel, use the following settings:

- **Framework Preset:** `Create React App`
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `build`
- **Install Command:** `npm install` (default)

## Environment Variables

The frontend relies on the backend API. If you deploy your backend to Render or another PaaS, you must provide its URL so the frontend can route traffic correctly.

Configure this in the Vercel project settings (Settings > Environment Variables):

| Name | Value | Environment |
| ---- | ----- | ----------- |
| `REACT_APP_API_URL` | `https://agentshield-backend-y16q.onrender.com` | Production, Preview, Development |

*Note: The frontend has a built-in fallback to the Render URL if this variable is omitted, but it is highly recommended to configure it explicitly.*

## Routing (Rewrites)

Because this is a Single Page Application using React Router, all unknown routes must redirect to `index.html`.

Vercel automatically detects Create React App and handles this rewrite by default. No manual `vercel.json` rewrite configuration is necessary unless you switch away from the standard `react-scripts` builder.

## WebSocket Configuration

The frontend dynamically upgrades the `REACT_APP_API_URL` from `http/https` to `ws/wss` for real-time WebSocket connections (e.g., Live SOC monitoring). 
Ensure your backend environment (like Render) supports WebSockets (which Render does natively). No additional Vercel configuration is required for WebSockets, as the client establishes the connection directly to the backend.
