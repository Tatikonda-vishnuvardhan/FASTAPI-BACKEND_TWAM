from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser
from . import repository
from .schemas import (
    GridParameters, PageParams, FilterParam, OrderParam,
    OrderItemGrid, OrderItemResponse, OrderItemCreate, OrderItemUpdate,
)

router = APIRouter(
    prefix="/api/OrderItems",
    tags=["OrderItems"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=OrderItemGrid, summary="Get paginated OrderItems grid")
def grid(
    pageNumber:  Optional[int] = Query(1,    ge=1),
    pageSize:    Optional[int] = Query(10,   ge=1, le=200),
    filterField: Optional[str] = Query(None),
    filterOp:    Optional[str] = Query("eq"),
    filterValue: Optional[str] = Query(None),
    orderField:  Optional[str] = Query(None),
    orderDir:    Optional[str] = Query("desc"),
    db: Session = Depends(get_db),
):
    filters = []
    if filterField and filterValue is not None:
        filters.append(FilterParam(field=filterField, operator=filterOp, value=filterValue))
    grid_params = GridParameters(
        page    = PageParams(pageNumber=pageNumber, pageSize=pageSize),
        filters = filters,
        order   = OrderParam(field=orderField, direction=orderDir),
    )
    return repository.get_order_items_grid(db=db, grid=grid_params)


@router.get("/{order_item_id}", response_model=OrderItemResponse)
def get_order_item(order_item_id: int, db: Session = Depends(get_db)):
    item = repository.get_order_item_by_id(db=db, order_item_id=order_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OrderItem not found")
    return item


@router.post("", response_model=OrderItemResponse, status_code=status.HTTP_201_CREATED)
def create_order_item(payload: OrderItemCreate, db: Session = Depends(get_db)):
    return repository.create_order_item(db=db, payload=payload)


@router.put("/{order_item_id}", response_model=OrderItemResponse)
def update_order_item(order_item_id: int, payload: OrderItemUpdate, db: Session = Depends(get_db)):
    item = repository.update_order_item(db=db, order_item_id=order_item_id, payload=payload)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OrderItem not found")
    return item


@router.delete("/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_item(order_item_id: int, db: Session = Depends(get_db)):
    if not repository.delete_order_item(db=db, order_item_id=order_item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OrderItem not found")