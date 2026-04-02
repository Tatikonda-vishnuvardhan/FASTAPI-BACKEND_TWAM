# BACKEND FIX #10 — Remove auth from DeliveryCharge (it's public lookup data)
# File: app/deliverycharge/routes.py
# Change: remove  dependencies=[Depends(get_current_user)]  from router

# BEFORE:
# router = APIRouter(
#     dependencies=[Depends(get_current_user)],
#     prefix="/api/DeliveryCharge", tags=["DeliveryCharge"])

# AFTER:
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles

router = APIRouter(
    # No router-level auth — delivery charges are public (needed during checkout)
    prefix="/api/DeliveryCharge",
    tags=["DeliveryCharge"]
)

def parse_filters(raw):
    if not raw: return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except: raise HTTPException(400, "Invalid Filters format.")

@router.get("/", response_model=schemas.DeliveryChargeListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all(
        db=db,
        filters=parse_filters(Filters),
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )

@router.get("/{delivery_charge_id}", response_model=schemas.DeliveryChargeResponse)
def get_detail(delivery_charge_id: int, db: Session = Depends(get_db)):
    result = repository.get_by_id(db, delivery_charge_id)
    if not result:
        raise HTTPException(status_code=404, detail="DeliveryCharge not found.")
    return result

@router.post("/", status_code=201, dependencies=[Depends(get_current_user)])
def create(command: schemas.DeliveryChargeCreate, db: Session = Depends(get_db)):
    return {"deliveryChargeId": repository.create(db, command)}

@router.put("/{delivery_charge_id}", dependencies=[Depends(get_current_user)])
def update(delivery_charge_id: int, command: schemas.DeliveryChargeUpdate, db: Session = Depends(get_db)):
    command.deliveryChargeId = delivery_charge_id
    result = repository.update(db, command)
    if not result:
        raise HTTPException(status_code=404, detail="DeliveryCharge not found.")
    return {"deliveryChargeId": result}

@router.delete("/{delivery_charge_id}", status_code=204, dependencies=[Depends(get_current_user)])
def delete(delivery_charge_id: int, db: Session = Depends(get_db)):
    if not repository.delete(db, delivery_charge_id):
        raise HTTPException(status_code=404, detail="DeliveryCharge not found.")
