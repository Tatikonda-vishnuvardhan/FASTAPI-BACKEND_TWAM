import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(prefix="/api/Address", tags=["Address"])


def parse_filters(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


@router.get("/", response_model=schemas.AddressListResponse, dependencies=[Depends(get_current_user)])
def get_addresses(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size",  ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all_addresses(
        db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size
    )


@router.get("/{address_id}", response_model=schemas.AddressResponse, dependencies=[Depends(get_current_user)])
def get_address(address_id: int, db: Session = Depends(get_db)):
    result = repository.get_address_by_id(db, address_id)
    if not result:
        raise HTTPException(status_code=404, detail="Address not found.")
    return result


@router.post("/", status_code=201)
def create_address(command: schemas.AddressCreate, db: Session = Depends(get_db)):
    repository.create_address(db, command)
    return {"success": True}


@router.put("/{address_id}", dependencies=[Depends(get_current_user)])
def update_address(address_id: int, command: schemas.AddressUpdate, db: Session = Depends(get_db)):
    result = repository.update_address(db, address_id, command)
    if not result:
        raise HTTPException(status_code=404, detail="Address not found.")
    return {"addressId": result}


@router.delete("/{address_id}", status_code=204, dependencies=[Depends(get_current_user)])
def delete_address(address_id: int, db: Session = Depends(get_db)):
    if not repository.delete_address(db, address_id):
        raise HTTPException(status_code=404, detail="Address not found.")