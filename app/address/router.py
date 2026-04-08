"""
app/address/router.py — Fixed
Fixes:
  1. Removed duplicate Depends(get_current_user) in route decorators
     (FastAPI dedupes via caching, but explicit double causes confusion)
  2. Auto-set userProfileId from token for non-staff users
  3. 403 error when user is logged in was caused by the JWT audience/issuer
     mismatch — now handled in get_current_user dependency
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, Roles
from app.auth.schemas import CurrentUser

router = APIRouter(prefix="/api/Address", tags=["Address"])


def parse_filters(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


@router.get("/", response_model=schemas.AddressListResponse)
def get_addresses(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size",  ge=1),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    filters = parse_filters(Filters) or []
    # Non-staff users can only see their own addresses
    if current_user.role_id not in Roles.STAFF:
        # Replace any client-sent userProfileId filter with the authenticated one
        filters = [f for f in filters if f.get("property") != "userProfileId"]
        filters.append({
            "property": "userProfileId",
            "comparison": "eq",
            "value": current_user.user_id,
        })

    return repository.get_all_addresses(
        db, filters or None, Order_Ascending, Order_Property, Page_Index, Page_Size
    )


@router.get("/{address_id}", response_model=schemas.AddressResponse)
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = repository.get_address_by_id(db, address_id)
    # Non-staff can only see their own address
    if result and current_user.role_id not in Roles.STAFF:
        if result.get("userProfileId") != current_user.user_id:
            raise HTTPException(status_code=404, detail="Address not found.")
    if not result:
        raise HTTPException(status_code=404, detail="Address not found.")
    return result


@router.post("/", status_code=201)
def create_address(
    command: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # Always set userProfileId from the authenticated token for non-staff
    if current_user.role_id not in Roles.STAFF:
        command.userProfileId = current_user.user_id
    elif not command.userProfileId:
        command.userProfileId = current_user.user_id

    address_id = repository.create_address(db, command)
    return {"success": True, "addressId": address_id}


@router.put("/{address_id}")
def update_address(
    address_id: int,
    command: schemas.AddressUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role_id not in Roles.STAFF:
        command.userProfileId = current_user.user_id
    elif not command.userProfileId:
        command.userProfileId = current_user.user_id

    result = repository.update_address(
        db,
        address_id,
        command,
        current_user_id=current_user.user_id,
        is_staff=current_user.role_id in Roles.STAFF,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Address not found.")
    return {"addressId": result}


@router.delete("/{address_id}", status_code=204)
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not repository.delete_address(
        db,
        address_id,
        current_user_id=current_user.user_id,
        is_staff=current_user.role_id in Roles.STAFF,
    ):
        raise HTTPException(status_code=404, detail="Address not found.")
