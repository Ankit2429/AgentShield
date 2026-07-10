# AgentShield Deployment Guide

This document describes how to deploy and run AgentShield in development and production environments.

## Development Setup

### Local Run
1. Install Python 3.11+ and Node.js 18+.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI Backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```
4. Install Node dependencies and start the Frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

### Docker Compose Run
To launch the full stack (backend and frontend) in containers:
```bash
docker-compose up --build
```
The backend will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.
