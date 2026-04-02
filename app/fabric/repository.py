from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from .models import Fabric

def _to_dict(f: Fabric) -> dict:
    return {
        "fabricId": f.fabricId, "name": f.name, "fabricCode": f.fabricCode,
        "userProfileId": f.userProfileId, "description": f.description,
        "texture": f.texture, "state": f.state, "isActive": f.isActive,
        "createdDate": f.createdDate, "modifiedDate": f.modifiedDate,
    }


def get_all_fabrics(db, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(Fabric).filter(Fabric.deletedInd == False, Fabric.isActive == True)
    query = apply_filters(query, Fabric, filters)
    query = apply_ordering(query, Fabric, order_property, order_ascending)
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return build_paged_response(total, [_to_dict(r) for r in query.all()])


def get_fabric_by_id(db, fabric_id: int) -> Optional[dict]:
    f = db.query(Fabric).filter(Fabric.fabricId == fabric_id, Fabric.deletedInd == False).first()
    return _to_dict(f) if f else None


def create_fabric(db, data) -> int:
    f = Fabric(
        name=data.name, fabricCode=data.fabricCode, userProfileId=data.userProfileId,
        description=data.description, texture=data.texture, state=data.state,
        isActive=data.isActive, createdDate=datetime.now(timezone.utc), deletedInd=False,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f.fabricId


def update_fabric(db, fabric_id: int, data) -> Optional[int]:
    f = db.query(Fabric).filter(Fabric.fabricId == fabric_id, Fabric.deletedInd == False).first()
    if not f:
        return None
    f.name=data.name; f.fabricCode=data.fabricCode; f.description=data.description
    f.texture=data.texture; f.isActive=data.isActive; f.state=data.state
    f.modifiedDate=datetime.now(timezone.utc)
    db.commit()
    return f.fabricId


def delete_fabric(db, fabric_id: int) -> bool:
    f = db.query(Fabric).filter(Fabric.fabricId == fabric_id, Fabric.deletedInd == False).first()
    if not f:
        return False
    f.deletedInd=True; f.modifiedDate=datetime.now(timezone.utc)
    db.commit()
    return True