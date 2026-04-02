import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/IntegrationLocation", tags=["IntegrationLocation"])

@router.get("/", response_model=schemas.IntegrationLocationListResponse)
def get_list(Filters: Optional[str]=Query(None,alias="Filters"), Order_Ascending: Optional[bool]=Query(None,alias="Order.Ascending"),
    Order_Property: Optional[str]=Query(None,alias="Order.Property"), Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_all(db, json.loads(Filters) if Filters else None, Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.get("/{integrationLocationId}", response_model=schemas.IntegrationLocationResponse)
def get_detail(integrationLocationId: int, db: Session=Depends(get_db)):
    result = repository.get_by_id(db, integrationLocationId)
    if not result: raise HTTPException(404, "IntegrationLocation not found.")
    return result

@router.post("/", status_code=201)
def create(command: schemas.IntegrationLocationCreate, db: Session=Depends(get_db)):
    return {"integrationLocationId": repository.create(db, command)}

@router.put("/{integrationLocationId}")
def update(integrationLocationId: int, command: schemas.IntegrationLocationUpdate, db: Session=Depends(get_db)):
    command.integrationLocationId = integrationLocationId
    result = repository.update(db, command)
    if not result: raise HTTPException(404, "IntegrationLocation not found.")
    return {"integrationLocationId": result}

@router.delete("/{integrationLocationId}", status_code=204)
def delete(integrationLocationId: int, db: Session=Depends(get_db)):
    if not repository.delete(db, integrationLocationId): raise HTTPException(404, "IntegrationLocation not found.")