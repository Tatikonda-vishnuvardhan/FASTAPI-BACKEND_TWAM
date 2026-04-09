import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/PackagingTemplates", tags=["PackagingTemplates"])

@router.get("", response_model=schemas.PackagingTemplatesListResponse)
def get_list(Filters: Optional[str]=Query(None,alias="Filters"), Order_Ascending: Optional[bool]=Query(None,alias="Order.Ascending"),
    Order_Property: Optional[str]=Query(None,alias="Order.Property"), Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_all(db, json.loads(Filters) if Filters else None, Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.get("/{packageId}", response_model=schemas.PackagingTemplatesResponse)
def get_detail(packageId: int, db: Session=Depends(get_db)):
    result = repository.get_by_id(db, packageId)
    if not result: raise HTTPException(404, "PackagingTemplates not found.")
    return result

@router.post("", status_code=201)
def create(command: schemas.PackagingTemplatesCreate, db: Session=Depends(get_db)):
    return {"packageId": repository.create(db, command)}

@router.put("/{packageId}")
def update(packageId: int, command: schemas.PackagingTemplatesUpdate, db: Session=Depends(get_db)):
    command.packageId = packageId
    result = repository.update(db, command)
    if not result: raise HTTPException(404, "PackagingTemplates not found.")
    return {"packageId": result}

@router.delete("/{packageId}", status_code=204)
def delete(packageId: int, db: Session=Depends(get_db)):
    if not repository.delete(db, packageId): raise HTTPException(404, "PackagingTemplates not found.")