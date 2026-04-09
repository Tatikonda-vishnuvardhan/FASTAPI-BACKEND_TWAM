import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Stores", tags=["Stores"])

@router.get("", response_model=schemas.StoresListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all(db, json.loads(Filters) if Filters else None,
                              Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.get("/{store_id}", response_model=schemas.StoresResponse)
def get_detail(store_id: int, db: Session = Depends(get_db)):
    result = repository.get_by_id(db, store_id)
    if not result: raise HTTPException(404, "Store not found.")
    return result

@router.post("", status_code=201)
def create(command: schemas.StoresCreate, db: Session = Depends(get_db)):
    return {"storeId": repository.create(db, command)}

@router.put("/{store_id}")
def update(store_id: int, command: schemas.StoresUpdate, db: Session = Depends(get_db)):
    command.storeId = store_id
    result = repository.update(db, command)
    if not result: raise HTTPException(404, "Store not found.")
    return {"storeId": result}

@router.delete("/{store_id}", status_code=204)
def delete(store_id: int, db: Session = Depends(get_db)):
    if not repository.delete(db, store_id): raise HTTPException(404, "Store not found.")