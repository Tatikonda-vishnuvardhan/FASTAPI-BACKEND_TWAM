import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/MessageTemplate", tags=["MessageTemplate"])

@router.get("", response_model=schemas.MessageTemplateListResponse)
def get_list(Filters: Optional[str]=Query(None,alias="Filters"), Order_Ascending: Optional[bool]=Query(None,alias="Order.Ascending"),
    Order_Property: Optional[str]=Query(None,alias="Order.Property"), Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_all(db, json.loads(Filters) if Filters else None, Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.get("/{messageTemplateId}", response_model=schemas.MessageTemplateResponse)
def get_detail(messageTemplateId: int, db: Session=Depends(get_db)):
    result = repository.get_by_id(db, messageTemplateId)
    if not result: raise HTTPException(404, "MessageTemplate not found.")
    return result

@router.post("", status_code=201)
def create(command: schemas.MessageTemplateCreate, db: Session=Depends(get_db)):
    return {"messageTemplateId": repository.create(db, command)}

@router.put("/{messageTemplateId}")
def update(messageTemplateId: int, command: schemas.MessageTemplateUpdate, db: Session=Depends(get_db)):
    command.messageTemplateId = messageTemplateId
    result = repository.update(db, command)
    if not result: raise HTTPException(404, "MessageTemplate not found.")
    return {"messageTemplateId": result}

@router.delete("/{messageTemplateId}", status_code=204)
def delete(messageTemplateId: int, db: Session=Depends(get_db)):
    if not repository.delete(db, messageTemplateId): raise HTTPException(404, "MessageTemplate not found.")