from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from typing import Optional, List
from datetime import datetime
from .models import Coupons


def get_all_coupons(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    query = db.query(Coupons).filter(Coupons.deletedInd == False)

    # Handle CouponCode filter with case-insensitive matching
    if filters:
        code_filters = [f for f in filters if f.get('property', '').lower() == 'couponcode']
        other_filters = [f for f in filters if f.get('property', '').lower() != 'couponcode']
        for cf in code_filters:
            query = query.filter(
                Coupons.couponCode.ilike(cf.get('value', ''))
            )
        filters = other_filters if other_filters else None

    query = apply_filters(query, Coupons, filters)

    query = apply_ordering(query, Coupons, order_property, order_ascending)

    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    return query.all()


def get_user_coupons(
    db: Session,
    user_profile_id: Optional[str] = None,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    query = db.query(Coupons).filter(Coupons.deletedInd == False)

    # Special UserProfileId filter — match ToUserProfileId OR IsCommon == true
    if user_profile_id:
        query = query.filter(
            or_(Coupons.toUserProfileId == user_profile_id, Coupons.isCommon == True)
        )

    # Apply remaining filters (excluding UserProfileId which is handled above)
    query = apply_filters(query, Coupons, filters)
    query = apply_ordering(query, Coupons, order_property, order_ascending)

    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    results = query.all()

    # Compute IsExpire field
    today = datetime.now().date()
    for coupon in results:
        if coupon.endDate:
            coupon.isExpire = today > coupon.endDate.date()
        else:
            coupon.isExpire = False

    return results


def get_coupon_by_id(db: Session, coupon_id: int):
    return db.query(Coupons).filter(
        Coupons.couponId == coupon_id,
        Coupons.deletedInd == False
    ).first()


def create_coupon(db: Session, coupon_data: dict):
    coupon = Coupons(
        **coupon_data,
        createdDate=datetime.now(),
        deletedInd=False
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def update_coupon(db: Session, coupon_id: int, coupon_data: dict):
    coupon = get_coupon_by_id(db, coupon_id)
    if not coupon:
        return None
    for key, value in coupon_data.items():
        setattr(coupon, key, value)
    coupon.modifiedDate = datetime.now()
    db.commit()
    db.refresh(coupon)
    return coupon


def delete_coupon(db: Session, coupon_id: int):
    coupon = get_coupon_by_id(db, coupon_id)
    if not coupon:
        return None
    coupon.deletedInd = True
    coupon.modifiedDate = datetime.now()
    db.commit()
    return True