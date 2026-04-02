import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

# GET routes are public (no auth) so the filter sidebar works for all users.
# POST / PUT / DELETE still require a logged-in user.
router = APIRouter(prefix="/api/Size", tags=["Size"])


@router.get("/", response_model=schemas.SizeListResponse)
def get_sizes(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    parsed_filters = None
    if Filters:
        try:
            parsed_filters = json.loads(Filters)
            if isinstance(parsed_filters, dict):
                parsed_filters = [parsed_filters]
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid Filters format.")

    sizes = repository.get_all_sizes(
        db=db,
        filters=parsed_filters,
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )

    response_list = [
        {
            "sizeId": s.sizeId,
            "sizeLabel": s.sizeLabel,
            "sizeCode": s.sizeCode,
            "description": s.description,
            "dimensions": s.dimensions,
            "state": s.state,
            "isActive": s.isActive,
            "isCupSize": s.isCupSize,
            "userProfileId": s.userProfileId,
            "orderNo": s.orderNo,
            "filters": None,
            "order": None,
            "page": None,
        }
        for s in sizes
    ]

    return {"count": len(response_list), "list": response_list, "parameters": None}


@router.get("/{size_id}", response_model=schemas.SizeResponse)
def get_size(size_id: int, db: Session = Depends(get_db)):
    size = repository.get_size_by_id(db, size_id)
    if not size:
        raise HTTPException(status_code=404, detail="Size not found")
    return size


@router.post("/", response_model=schemas.SizeResponse, status_code=201,
             dependencies=[Depends(get_current_user)])
def create_size(size: schemas.SizeCreate, db: Session = Depends(get_db)):
    return repository.create_size(db, size.model_dump())


@router.put("/{size_id}", response_model=schemas.SizeResponse,
            dependencies=[Depends(get_current_user)])
def update_size(size_id: int, size: schemas.SizeUpdate, db: Session = Depends(get_db)):
    updated = repository.update_size(db, size_id, size.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Size not found")
    return updated


@router.delete("/{size_id}", status_code=204,
               dependencies=[Depends(get_current_user)])
def delete_size(size_id: int, db: Session = Depends(get_db)):
    result = repository.delete_size(db, size_id)
    if not result:
        raise HTTPException(status_code=404, detail="Size not found")
