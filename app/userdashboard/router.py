import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from app.auth.dependencies import get_current_user, Roles
from . import schemas, repository

router = APIRouter(prefix="/api/UserDashboard", tags=["UserDashboard"])


@router.post("/GetUserDashboard", response_model=schemas.UserDashboardResponse,
             )
def get_user_dashboard(command: schemas.UserDashboardRequest, db: Session = Depends(get_db)):
    return repository.get_dashboard(db, command.userProfileId or "")


# ── PUBLIC ────────────────────────────────────────────────────────────────────
@router.get("/GetProductMessage")
def get_product_message(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_product_messages(db,
        json.loads(Filters) if Filters else None,
        Order_Ascending, Order_Property, Page_Index, Page_Size)