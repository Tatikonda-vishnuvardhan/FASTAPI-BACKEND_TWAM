import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

# GET routes are public (no auth) so the filter sidebar works for all users.
# POST / PUT / DELETE still require a logged-in user.
router = APIRouter(prefix="/api/CupSize", tags=["CupSize"])


@router.get("", response_model=schemas.CupSizeListResponse)
def get_cupsizes(
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

    cupsizes = repository.get_all_cupsizes(
        db=db,
        filters=parsed_filters,
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )

    response_list = [
        {
            "cupSizeId": c.cupSizeId,
            "sizeLabel": c.sizeLabel,
            "dimensions": c.dimensions,
            "state": c.state,
            "isActive": c.isActive,
            "userProfileId": c.userProfileId,
            "filters": None,
            "order": None,
            "page": None,
        }
        for c in cupsizes
    ]

    return {"count": len(response_list), "list": response_list, "parameters": None}


@router.get("/{cupsize_id}", response_model=schemas.CupSizeResponse)
def get_cupsize(cupsize_id: int, db: Session = Depends(get_db)):
    cupsize = repository.get_cupsize_by_id(db, cupsize_id)
    if not cupsize:
        raise HTTPException(status_code=404, detail="CupSize not found")
    return cupsize


@router.post("", response_model=schemas.CupSizeResponse, status_code=201,
             dependencies=[Depends(get_current_user)])
def create_cupsize(cupsize: schemas.CupSizeCreate, db: Session = Depends(get_db)):
    return repository.create_cupsize(db, cupsize.model_dump())


@router.put("/{cupsize_id}", response_model=schemas.CupSizeResponse,
            dependencies=[Depends(get_current_user)])
def update_cupsize(cupsize_id: int, cupsize: schemas.CupSizeUpdate, db: Session = Depends(get_db)):
    updated = repository.update_cupsize(db, cupsize_id, cupsize.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="CupSize not found")
    return updated


@router.delete("/{cupsize_id}", status_code=204,
               dependencies=[Depends(get_current_user)])
def delete_cupsize(cupsize_id: int, db: Session = Depends(get_db)):
    result = repository.delete_cupsize(db, cupsize_id)
    if not result:
        raise HTTPException(status_code=404, detail="CupSize not found")