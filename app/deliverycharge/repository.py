from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import DeliveryCharge

def _get_shipping_type(db: Session, shipping_type_id):
    if not shipping_type_id:
        return None
    row = db.execute(
        text('SELECT "ShippingTypeId", "ShippingType" FROM mdm."ShippingType" WHERE "ShippingTypeId" = :id LIMIT 1'),
        {"id": shipping_type_id}
    ).fetchone()
    if row:
        return {"shippingTypeId": row[0], "shippingType": row[1]}
    return None


def _to_response(db: Session, entity: DeliveryCharge) -> dict:
    return {
        "deliveryChargeId": entity.deliveryChargeId,
        "shippingTypeId": entity.shippingTypeId,
        "deliveryCharges": float(entity.deliveryCharges) if entity.deliveryCharges else None,
        "orderValueRange": entity.orderValueRange,
        "state": entity.state,
        "isActive": entity.isActive,
        "days": entity.days,
        "isFree": entity.isFree,
        "description": entity.description,
        "userProfileId": entity.userProfileId,
        "shippingType": _get_shipping_type(db, entity.shippingTypeId),
    }


# ── Get List ──────────────────────────────────────────────────────────────────

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(DeliveryCharge).filter(DeliveryCharge.deletedInd == False)
    query = apply_filters(query, DeliveryCharge, filters)

    query = apply_ordering(query, DeliveryCharge, order_property, order_ascending)
    total = query.count()

    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)

    rows = query.all()
    return {
        "count": total,
        "list": [_to_response(db, r) for r in rows],
        "parameters": None
    }


# ── Get By ID ─────────────────────────────────────────────────────────────────

def get_by_id(db: Session, delivery_charge_id: int) -> Optional[dict]:
    entity = db.query(DeliveryCharge).filter(
        DeliveryCharge.deliveryChargeId == delivery_charge_id,
        DeliveryCharge.deletedInd == False
    ).first()
    if not entity:
        return None
    return _to_response(db, entity)


# ── Create ────────────────────────────────────────────────────────────────────

def create(db: Session, data) -> int:
    entity = DeliveryCharge(
        shippingTypeId=data.shippingTypeId,
        deliveryCharges=data.deliveryCharges,
        orderValueRange=data.orderValueRange,
        days=data.days,
        isFree=data.isFree,
        description=data.description,
        state=data.state,
        isActive=data.isActive,
        userProfileId=data.userProfileId,
        createdDate=datetime.now(timezone.utc),
        deletedInd=False,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity.deliveryChargeId


# ── Update ────────────────────────────────────────────────────────────────────

def update(db: Session, data) -> Optional[int]:
    entity = db.query(DeliveryCharge).filter(
        DeliveryCharge.deliveryChargeId == data.deliveryChargeId
    ).first()
    if not entity:
        return None
    entity.shippingTypeId = data.shippingTypeId
    entity.deliveryCharges = data.deliveryCharges
    entity.orderValueRange = data.orderValueRange
    entity.days = data.days
    entity.isFree = data.isFree
    entity.description = data.description
    entity.state = data.state
    entity.isActive = data.isActive
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return entity.deliveryChargeId


# ── Delete ────────────────────────────────────────────────────────────────────

def delete(db: Session, delivery_charge_id: int) -> bool:
    entity = db.query(DeliveryCharge).filter(
        DeliveryCharge.deliveryChargeId == delivery_charge_id
    ).first()
    if not entity:
        return False
    entity.deletedInd = True
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True