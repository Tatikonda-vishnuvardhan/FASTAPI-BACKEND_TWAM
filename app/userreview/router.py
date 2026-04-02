import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/UserReview", tags=["UserReview"])

@router.get("/", response_model=schemas.UserReviewListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all(
        db, json.loads(Filters) if Filters else None,
        Order_Ascending, Order_Property, Page_Index, Page_Size
    )

@router.get("/{review_id}", response_model=schemas.UserReviewResponse)
def get_detail(review_id: int, db: Session = Depends(get_db)):
    result = repository.get_by_id(db, review_id)
    if not result:
        raise HTTPException(404, "UserReview not found.")
    return result

@router.post("/", status_code=201)
def create(
    command: schemas.UserReviewCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),   # ← auth required
):
    # Always bind to logged-in user
    command.userProfileId = current_user.user_id
    return {"userReviewId": repository.create(db, command)}

@router.put("/{review_id}")
def update(
    review_id: int,
    command: schemas.UserReviewUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    command.userReviewId = review_id
    result = repository.update(db, command)
    if not result:
        raise HTTPException(404, "UserReview not found.")
    return {"userReviewId": result}