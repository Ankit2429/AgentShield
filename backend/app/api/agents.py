from fastapi import APIRouter
from typing import List
from app.models.agent import Agent

router = APIRouter(prefix="/api/agents", tags=["Agents"])

@router.get("", response_model=List[Agent])
def list_agents():
    # Placeholder
    return [
        {"id": 1, "name": "Agent Alpha", "description": "Primary task router", "role": "router", "trust_score": 0.95},
        {"id": 2, "name": "Agent Beta", "description": "Database reader helper", "role": "reader", "trust_score": 0.85}
    ]
