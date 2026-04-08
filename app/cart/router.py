import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Cart", tags=["Cart"])


def parse_filters(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


# ── GET /api/Cart ─────────────────────────────────────────────────────────────
@router.get("/", response_model=schemas.CartListResponse)
def get_cart_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    filters = parse_filters(Filters) or []
    if current_user.role_id not in Roles.STAFF:
        filters.append({
            "property": "userProfileId",
            "comparison": "eq",
            "value": current_user.user_id,
        })
    return repository.get_cart_list(
        db=db,
        filters=filters or None,
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )


# ── POST /api/Cart — IMPROVED ─────────────────────────────────────────────────
@router.post("/", status_code=201)
def create_cart(
    cart: schemas.CartCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    IMPROVED: Returns detailed response with status info.
    
    Response includes:
    - cartId: ID of cart item (new or existing)
    - status: "created" or "updated"
    - quantity: Current quantity after operation
    - message: Human-readable message
    """
    if not cart.userProfileId:
        cart.userProfileId = current_user.user_id
    result = repository.create_cart(db, cart)
    return result


# ── POST /api/Cart/BulkCart — IMPROVED ────────────────────────────────────────
@router.post("/BulkCart", status_code=200)
def bulk_cart(
    command: schemas.BulkCartCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    IMPROVED: Returns detailed sync statistics.
    
    Response includes:
    - success: True if completed
    - added: Number of new items created
    - updated: Number of items with quantity updated
    - skipped: Number of items already present with same qty
    - total: Total items processed
    - message: Summary message
    """
    if not command.createCartCommands:
        raise HTTPException(status_code=400, detail="No cart items provided.")
    
    result = repository.create_bulk_cart(
        db, 
        command.createCartCommands, 
        command.userProfileId or current_user.user_id
    )
    return result


# ── PUT /api/Cart/{Id} ────────────────────────────────────────────────────────
@router.put("/{cart_id}")
def update_cart(
    cart_id: int,
    command: schemas.CartUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = repository.update_cart(db, cart_id, command.quantity, current_user.user_id, current_user.role_id in Roles.STAFF)
    if result is None:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    return {"cartId": result, "message": "Cart updated successfully"}


# ── DELETE /api/Cart/{Id} ─────────────────────────────────────────────────────
@router.delete("/{cart_id}", status_code=204)
def delete_cart(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = repository.delete_cart(db, cart_id, current_user.user_id, current_user.role_id in Roles.STAFF)
    if not result:
        raise HTTPException(status_code=404, detail="Cart item not found.")


# ── POST /api/Cart/DeleteMutiple ──────────────────────────────────────────────
@router.post("/DeleteMutiple", status_code=204)
def delete_multiple(
    ids: List[int],
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = repository.delete_multiple_carts(db, ids, current_user.user_id, current_user.role_id in Roles.STAFF)
    if not result:
        raise HTTPException(status_code=404, detail="No cart items found for the given IDs.")
