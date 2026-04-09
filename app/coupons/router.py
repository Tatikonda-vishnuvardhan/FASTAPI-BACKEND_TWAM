import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from app.auth.dependencies import get_current_user, Roles
from . import schemas, repository

router = APIRouter(prefix="/api/Coupons", tags=["Coupons"])


def _pf(Filters):
    if not Filters: return None
    try:
        p = json.loads(Filters)
        return p if isinstance(p, list) else [p]
    except: raise HTTPException(400, "Invalid Filters format.")


# ── PUBLIC ────────────────────────────────────────────────────────────────────
@router.get("", response_model=schemas.CouponListResponse)
def get_coupons(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    coupons = repository.get_all_coupons(db, _pf(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size)
    return {"count": len(coupons), "list": [
        {"couponId": c.couponId, "couponCode": c.couponCode, "couponName": c.couponName,
         "description": c.description, "discount": c.discount, "startDate": c.startDate,
         "endDate": c.endDate, "state": c.state, "isActive": c.isActive, "isCommon": c.isCommon,
         "toUserProfileId": c.toUserProfileId, "filters": None, "order": None, "page": None}
        for c in coupons], "parameters": None}


@router.get("/UserList", response_model=schemas.CouponUserListResponse)
def get_user_coupons(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    pf = _pf(Filters)
    uid = next((f.get("value") for f in (pf or []) if f.get("property") == "UserProfileId"), None)
    coupons = repository.get_user_coupons(db, uid, pf, Order_Ascending, Order_Property, Page_Index, Page_Size)
    return {"count": len(coupons), "list": [
        {"couponId": c.couponId, "couponCode": c.couponCode, "couponName": c.couponName,
         "description": c.description, "discount": c.discount, "startDate": c.startDate,
         "endDate": c.endDate, "state": c.state, "isActive": c.isActive, "isCommon": c.isCommon,
         "toUserProfileId": c.toUserProfileId, "isExpire": getattr(c, "isExpire", None),
         "filters": None, "order": None, "page": None}
        for c in coupons], "parameters": None}


@router.get("/{coupon_id}", response_model=schemas.CouponResponse)
def get_coupon(coupon_id: int, db: Session = Depends(get_db)):
    coupon = repository.get_coupon_by_id(db, coupon_id)
    if not coupon: raise HTTPException(404, "Coupon not found")
    return coupon


# ── LOGGED IN ─────────────────────────────────────────────────────────────────
@router.post("", response_model=schemas.CouponResponse, status_code=201,
             dependencies=[Depends(get_current_user)])
def create_coupon(coupon: schemas.CouponCreate, db: Session = Depends(get_db)):
    return repository.create_coupon(db, coupon.model_dump())


@router.put("/{coupon_id}", response_model=schemas.CouponResponse,
            dependencies=[Depends(get_current_user)])
def update_coupon(coupon_id: int, coupon: schemas.CouponUpdate, db: Session = Depends(get_db)):
    updated = repository.update_coupon(db, coupon_id, coupon.model_dump(exclude_unset=True))
    if not updated: raise HTTPException(404, "Coupon not found")
    return updated


@router.delete("/{coupon_id}", status_code=204,
               dependencies=[Depends(get_current_user)])
def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    if not repository.delete_coupon(db, coupon_id): raise HTTPException(404, "Coupon not found")