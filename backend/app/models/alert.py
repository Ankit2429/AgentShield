from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AlertBase(BaseModel):
    title: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    agent_id: Optional[int] = None

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: int
    timestamp: datetime
    resolved: bool = False

    class Config:
        from_attributes = True
