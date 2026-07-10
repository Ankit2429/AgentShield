from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_stats():
    # Placeholder
    return {
        "active_agents": 2,
        "total_messages": 150,
        "unresolved_alerts": 1,
        "system_status": "SECURE"
    }
