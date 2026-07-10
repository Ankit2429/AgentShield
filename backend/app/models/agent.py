from pydantic import BaseModel
from typing import Optional

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    role: str
    trust_score: float = 1.0

class AgentCreate(AgentBase):
    pass

class Agent(AgentBase):
    id: int

    class Config:
        from_attributes = True
