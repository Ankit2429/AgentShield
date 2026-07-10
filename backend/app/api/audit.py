from fastapi import APIRouter
from typing import List
from datetime import datetime
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/audit", tags=["Audit"])

@router.get("", response_model=List[AuditLog])
def list_audit_logs():
    # Placeholder
    return [
        {"id": 1, "action": "AGENT_REGISTRATION", "details": "Agent Alpha registered successfully", "operator": "SYSTEM", "timestamp": datetime.now()}
    ]
