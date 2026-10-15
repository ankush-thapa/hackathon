from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationItem
from app.services.notification_service import _item

router = APIRouter(tags=["notifications"])


class NotificationHistoryResponse(BaseModel):
    items: list[NotificationItem]
    next_cursor: str | None = None


@router.get("/v1/notifications/history", response_model=NotificationHistoryResponse)
def history(cursor: int | None = Query(default=None, gt=0, le=2**64-1),
            limit: int = Query(default=20, ge=1, le=50),
            user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Read and unread notifications; pass next_cursor to fetch older entries."""
    query = select(Notification).where(Notification.id_user == user)
    if cursor is not None: query = query.where(Notification.id_notification < cursor)
    rows = list(db.scalars(query.order_by(Notification.id_notification.desc()).limit(limit+1)))
    return NotificationHistoryResponse(items=[_item({c.name: getattr(n,c.name) for c in Notification.__table__.columns})
        for n in rows[:limit]], next_cursor=str(rows[limit-1].id_notification) if len(rows)>limit else None)
