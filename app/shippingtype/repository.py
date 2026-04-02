from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import ShippingType

def _to_dict(s: ShippingType) -> dict:
    return {
        "shippingTypeId":   s.shippingTypeId,
        "shippingTypeName": s.shippingTypeName,
        "state":            s.state,
        "isActive":         s.isActive,
        "userProfileId":    s.userProfileId,
        "createdDate":      s.createdDate,
        "modifiedDate":     s.modifiedDate,
    }


def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(ShippingType).filter(ShippingType.deletedInd == False)

    query = apply_filters(query, ShippingType, filters)
    query = apply_ordering(query, ShippingType, order_property, order_ascending)

    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)

    return build_paged_response(total, [_to_dict(r) for r in query.all()])


def get_by_id(db: Session, shipping_type_id: int) -> Optional[dict]:
    s = db.query(ShippingType).filter(
        ShippingType.shippingTypeId == shipping_type_id,
        ShippingType.deletedInd == False
    ).first()
    return _to_dict(s) if s else None


def create(db: Session, data) -> int:
    s = ShippingType(
        shippingTypeName = data.shippingTypeName,
        state            = data.state,
        isActive         = data.isActive,
        userProfileId    = data.userProfileId,
        createdDate      = datetime.now(timezone.utc),
        deletedInd       = False,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.shippingTypeId


def update(db: Session, shipping_type_id: int, data) -> Optional[int]:
    s = db.query(ShippingType).filter(
        ShippingType.shippingTypeId == shipping_type_id,
        ShippingType.deletedInd == False
    ).first()
    if not s:
        return None
    s.shippingTypeName = data.shippingTypeName
    s.state            = data.state
    s.isActive         = data.isActive
    s.modifiedDate     = datetime.now(timezone.utc)
    db.commit()
    return s.shippingTypeId


def delete(db: Session, shipping_type_id: int) -> bool:
    s = db.query(ShippingType).filter(
        ShippingType.shippingTypeId == shipping_type_id,
        ShippingType.deletedInd == False
    ).first()
    if not s:
        return False
    s.deletedInd   = True
    s.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True