import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/State", tags=["State"])


def parse_filters(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


@router.get("", response_model=schemas.StateListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all(db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size)


@router.get("/{state_id}", response_model=schemas.StateResponse)
def get_detail(state_id: int, db: Session = Depends(get_db)):
    result = repository.get_by_id(db, state_id)
    if not result:
        raise HTTPException(status_code=404, detail="State not found.")
    return result


@router.post("", status_code=201)
def create(command: schemas.StateCreate, db: Session = Depends(get_db)):
    return {"stateId": repository.create(db, command)}


@router.put("/{state_id}")
def update(state_id: int, command: schemas.StateUpdate, db: Session = Depends(get_db)):
    command.stateId = state_id
    result = repository.update(db, command)
    if not result:
        raise HTTPException(status_code=404, detail="State not found.")
    return {"stateId": result}


@router.delete("/{state_id}", status_code=204)
def delete(state_id: int, db: Session = Depends(get_db)):
    if not repository.delete(db, state_id):
        raise HTTPException(status_code=404, detail="State not found.")