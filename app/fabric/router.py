import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Fabric", tags=["Fabric"])

def parse_filters(raw):
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


@router.get("", response_model=schemas.FabricListResponse)
def get_fabrics(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size",  ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all_fabrics(db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size)


@router.get("/{fabric_id}", response_model=schemas.FabricResponse)
def get_fabric(fabric_id: int, db: Session = Depends(get_db)):
    result = repository.get_fabric_by_id(db, fabric_id)
    if not result:
        raise HTTPException(status_code=404, detail="Fabric not found.")
    return result


@router.post("", status_code=201)
def create_fabric(command: schemas.FabricCreate, db: Session = Depends(get_db)):
    return {"fabricId": repository.create_fabric(db, command)}


@router.put("/{fabric_id}")
def update_fabric(fabric_id: int, command: schemas.FabricUpdate, db: Session = Depends(get_db)):
    result = repository.update_fabric(db, fabric_id, command)
    if not result:
        raise HTTPException(status_code=404, detail="Fabric not found.")
    return {"fabricId": result}


@router.delete("/{fabric_id}", status_code=204)
def delete_fabric(fabric_id: int, db: Session = Depends(get_db)):
    if not repository.delete_fabric(db, fabric_id):
        raise HTTPException(status_code=404, detail="Fabric not found.")