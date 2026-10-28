"""事件上报接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_visitor_id
from ..schemas.event import EventAcceptedOut, EventBatchIn
from ..services.events import EventService

router = APIRouter(tags=["events"])


@router.post("/api/events", response_model=EventAcceptedOut)
def post_events(
    payload: EventBatchIn,
    db: Session = Depends(get_db),
    visitor_id: str = Depends(get_visitor_id),
) -> EventAcceptedOut:
    """批量上报事件（≤20 条）；个别事件非法不影响其余落库。"""
    result = EventService.ingest(db, visitor_id, payload.session_id, payload.events)
    return EventAcceptedOut(accepted=result.accepted, dropped=result.dropped)
