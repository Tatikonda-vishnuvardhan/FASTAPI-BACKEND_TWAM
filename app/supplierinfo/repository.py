from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import SupplierInfo

def _to_dict(r: SupplierInfo) -> dict:
    return {
        "supplierInfoId": r.supplierInfoId, "supplierName": r.supplierName,
        "supplierAddress": r.supplierAddress, "supplierGSTNumber": r.supplierGSTNumber,
        "supplierGSTAmount": float(r.supplierGSTAmount) if r.supplierGSTAmount is not None else None,
        "signature": r.signature, "state": r.state, "isActive": r.isActive,
        "userProfileId": r.userProfileId, "createdDate": r.createdDate
    }

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(SupplierInfo).filter(SupplierInfo.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(SupplierInfo, f.get("property", ""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(SupplierInfo, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index - 1) * page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, id_val: int):
    r = db.query(SupplierInfo).filter(SupplierInfo.supplierInfoId == id_val, SupplierInfo.deletedInd == False).first()
    return _to_dict(r) if r else None

def create(db: Session, data) -> int:
    entity = SupplierInfo(
        supplierName=data.supplierName, supplierAddress=data.supplierAddress,
        supplierGSTNumber=data.supplierGSTNumber, supplierGSTAmount=data.supplierGSTAmount,
        signature=data.signature, state=data.state, isActive=data.isActive,
        userProfileId=data.userProfileId, createdDate=datetime.now(timezone.utc), deletedInd=False
    )
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.supplierInfoId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(SupplierInfo).filter(SupplierInfo.supplierInfoId == data.supplierInfoId).first()
    if not entity: return None
    entity.supplierName = data.supplierName; entity.supplierAddress = data.supplierAddress
    entity.supplierGSTNumber = data.supplierGSTNumber; entity.supplierGSTAmount = data.supplierGSTAmount
    entity.signature = data.signature; entity.state = data.state
    entity.isActive = data.isActive; entity.userProfileId = data.userProfileId
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.supplierInfoId

def delete(db: Session, id_val: int) -> bool:
    entity = db.query(SupplierInfo).filter(SupplierInfo.supplierInfoId == id_val).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True