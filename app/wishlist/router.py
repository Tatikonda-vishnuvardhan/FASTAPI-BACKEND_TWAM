import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from database import get_db

from . import schemas, repository
from app.auth.dependencies import get_current_user, get_optional_user, CurrentUser

router = APIRouter(prefix="/api/Wishlist", tags=["Wishlist"])


# ==================== PUBLIC ENDPOINTS (Guest + Logged-in) ====================

@router.get("", response_model=schemas.WishlistListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Works for both Guest and Logged-in users"""
    filters = json.loads(Filters) if Filters else []

    return repository.get_all(
        db, filters, Order_Ascending, Order_Property, Page_Index, Page_Size
    )


# ── POST /api/Wishlist — IMPROVED ─────────────────────────────────────────────
@router.post("", status_code=201)
def create(
    command: schemas.WishlistCreate,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """
    IMPROVED: Returns detailed response with status info.
    
    Response includes:
    - wishlistId: ID of wishlist item (new or existing)
    - status: "created" or "existing"
    - message: Human-readable message
    """
    user_profile_id = current_user.user_id if current_user else command.userProfileId or "GUEST"
    command.userProfileId = user_profile_id

    result = repository.create(db, command)
    return result


@router.delete("/{wishlist_id}", status_code=204)
def delete(
    wishlist_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """Delete works for both (we don't strict check ownership for simplicity)"""
    if not repository.delete(db, wishlist_id):
        raise HTTPException(404, "Wishlist item not found.")


@router.delete("/DeleteVariantWishlist/{product_variant_id}", status_code=204)
def delete_variant(
    product_variant_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
):
    if not repository.delete_by_variant(db, product_variant_id):
        raise HTTPException(404, "Wishlist item not found.")


# ==================== SYNC ENDPOINT — IMPROVED ================================

@router.post("/sync", status_code=200)
def sync_guest_wishlist(
    command: schemas.BulkWishlistCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),   # Must be logged in
):
    """
    IMPROVED: Sync guest wishlist to logged-in user account with detailed stats.
    
    Call this right after successful login/signup.
    
    Response includes:
    - success: True if completed
    - added: Number of new items created
    - skipped: Number of items already in wishlist
    - total: Total items processed
    - message: Summary message
    """
    if not command.createWishlistCommands:
        return {
            "success": True,
            "added": 0,
            "skipped": 0,
            "total": 0,
            "message": "No items to sync"
        }

    result = repository.create_bulk(
        db,
        items=command.createWishlistCommands,
        user_profile_id=current_user.user_id
    )
    
    return result


# ==================== BULK CREATE ENDPOINT (Alternative to sync) ==============

@router.post("/bulk", status_code=200)
def bulk_create(
    command: schemas.BulkWishlistCreate,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """
    IMPROVED: Bulk create wishlist items with detailed statistics.
    
    Works for both guest and authenticated users.
    """
    if not command.createWishlistCommands:
        return {
            "success": True,
            "added": 0,
            "skipped": 0,
            "total": 0,
            "message": "No items provided"
        }

    user_profile_id = current_user.user_id if current_user else command.userProfileId or "GUEST"
    
    result = repository.create_bulk(
        db,
        items=command.createWishlistCommands,
        user_profile_id=user_profile_id
    )
    
    return result


@router.get("/Wishlist")
def list_wishlist(userProfileId: str, db: Session = Depends(get_db)):
    return repository.get_user_wishlist(db, userProfileId)