from pydantic import BaseModel
from datetime import datetime

class AuditLogBase(BaseModel):
    action: str
    details: str
    operator: str

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
