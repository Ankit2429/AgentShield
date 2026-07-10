from fastapi import APIRouter
from typing import List
from datetime import datetime
from app.models.message import Message

router = APIRouter(prefix="/api/messages", tags=["Messages"])

@router.get("", response_model=List[Message])
def list_messages():
    # Placeholder
    return [
        {"id": 1, "sender_id": 1, "receiver_id": 2, "content": "Fetch system stats", "timestamp": datetime.now()}
    ]
