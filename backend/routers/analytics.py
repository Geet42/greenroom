from fastapi import APIRouter, BackgroundTasks, Depends

from auth import AuthenticatedUser, get_current_user
from models import AnalyticsEventRequest
from services.persistence import persist_analytics_event

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/event", status_code=202)
async def track_event(
    req: AnalyticsEventRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Fire-and-forget usage/click tracking — used to spot usage spikes and
    drop-off points. Persistence runs in the background so a slow or failed
    write never delays or breaks the caller's UI action."""
    background_tasks.add_task(
        persist_analytics_event, user.id, req.session_id, req.event, req.properties,
    )
    return {"status": "accepted"}
