"""Demo router for AgentShield API v1.

Endpoint
--------
``POST /api/v1/demo/seed``

Manually triggers the demo data seeder.  Only available when DEMO_MODE is
enabled.  Restricted to the Admin role.

Designed for use in development and presentation environments where the
in-memory state was cleared (e.g. after a backend restart during a demo).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_roles
from app.config import settings

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    summary="Seed Demo Data",
    dependencies=[Depends(require_roles("Admin"))],
    description=(
        "Triggers the demo data seeder to populate the dashboard with "
        "realistic agent interactions.  Only available when DEMO_MODE=True. "
        "Idempotent: exits immediately if sessions already exist."
    ),
)
async def seed_demo(force: bool = False) -> dict:
    """Manually seed demo data.

    Args:
        force: If True, bypasses the idempotency check and re-seeds even when
               sessions already exist.  Use with care - this adds duplicate
               sessions on top of existing data.

    Returns:
        dict with ``status`` and ``message`` fields.

    Raises:
        HTTPException 403: When DEMO_MODE is disabled.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is only available when DEMO_MODE is enabled.",
        )

    from app.core.demo_seeder import run_demo_seed, _SCENARIOS

    if force:
        # Temporarily bypass idempotency by clearing sessions first.
        # This is intentionally simple - for demo use only.
        from app.api.deps import _replay_engine
        with _replay_engine._lock:
            _replay_engine._sessions.clear()

    await run_demo_seed()

    return {
        "status": "ok",
        "message": f"Demo seed complete. {len(_SCENARIOS)} agent scenarios processed.",
        "demo_mode": settings.DEMO_MODE,
    }
