from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from .models import TaxHSNCode

def _to_dict(r: TaxHSNCode) -> dict:
    return {
        "taxHSNCodeId": r.taxHSNCodeId,
        "hsnCode": r.hsnCode,
        "hsnDescription": r.hsnDescription,
        "cgst": float(r.cgst) if r.cgst else None,
        "sgst": float(r.sgst) if r.sgst else None,
        "totalGST": float(r.totalGST) if r.totalGST else None,
        "userProfileId": r.userProfileId,
        "state": r.state,
        "isActive": r.isActive,
    }


def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(TaxHSNCode).filter(TaxHSNCode.deletedInd == False, TaxHSNCode.isActive == True)
    query = apply_filters(query, TaxHSNCode, filters)
    query = apply_ordering(query, TaxHSNCode, order_property, order_ascending)
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return build_paged_response(total, [_to_dict(r) for r in query.all()])


def get_by_id(db: Session, tax_id: int) -> Optional[dict]:
    entity = db.query(TaxHSNCode).filter(TaxHSNCode.taxHSNCodeId == tax_id, TaxHSNCode.deletedInd == False).first()
    return _to_dict(entity) if entity else None


def create(db: Session, data) -> int:
    entity = TaxHSNCode(
        hsnCode=data.hsnCode,
        hsnDescription=data.hsnDescription,
        cgst=data.cgst,
        sgst=data.sgst,
        totalGST=data.totalGST,
        userProfileId=data.userProfileId,
        state=data.state,
        isActive=data.isActive,
        createdDate=datetime.now(timezone.utc),
        deletedInd=False,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity.taxHSNCodeId


def update(db: Session, data) -> Optional[int]:
    entity = db.query(TaxHSNCode).filter(TaxHSNCode.taxHSNCodeId == data.taxHSNCodeId).first()
    if not entity:
        return None
    entity.hsnCode = data.hsnCode
    entity.hsnDescription = data.hsnDescription
    entity.cgst = data.cgst
    entity.sgst = data.sgst
    entity.totalGST = data.totalGST
    entity.state = data.state
    entity.isActive = data.isActive
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return entity.taxHSNCodeId


def delete(db: Session, tax_id: int) -> bool:
    entity = db.query(TaxHSNCode).filter(TaxHSNCode.taxHSNCodeId == tax_id).first()
    if not entity:
        return False
    entity.deletedInd = True
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True