from fastapi import APIRouter
from typing import List
from datetime import datetime
from app.models.alert import Alert

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("", response_model=List[Alert])
def list_alerts():
    # Placeholder
    return [
        {"id": 1, "title": "Unauthorized Command Attempt", "description": "Agent Beta tried to write to logs direct", "severity": "HIGH", "agent_id": 2, "timestamp": datetime.now(), "resolved": False}
    ]
