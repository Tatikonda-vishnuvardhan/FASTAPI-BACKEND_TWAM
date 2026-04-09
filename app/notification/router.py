# BACKEND FIX #11 — Notification stub module
# Add to main.py:
#   from app.notification.routes import router as notification_router
#   app.include_router(notification_router)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/api/Notification",
    tags=["Notification"],
    dependencies=[Depends(get_current_user)]
)

@router.get("")
def get_notifications(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    """Stub — returns empty list until notifications are implemented."""
    return {"count": 0, "list": [], "parameters": None}