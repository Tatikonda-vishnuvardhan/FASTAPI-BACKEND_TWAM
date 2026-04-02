from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import PackagingTemplates

def _to_dict(r):
    d = {"packageId": r.packageId, "createdDate": r.createdDate}
    for attr in ['packageName', 'state', 'isActive', 'userProfileId']:
        v = getattr(r, attr, None)
        d[attr] = float(v) if v is not None and hasattr(v, "__float__") and not isinstance(v, (bool,int,str)) else v
    return d

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(PackagingTemplates).filter(PackagingTemplates.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(PackagingTemplates, f.get("property",""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(PackagingTemplates, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index-1)*page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, id_val: int):
    r = db.query(PackagingTemplates).filter(PackagingTemplates.packageId == id_val, PackagingTemplates.deletedInd == False).first()
    return _to_dict(r) if r else None

def create(db: Session, data) -> int:
    entity = PackagingTemplates(
        packageName=data.packageName,
        state=data.state,
        isActive=data.isActive,
        userProfileId=data.userProfileId,
        createdDate=datetime.now(timezone.utc), deletedInd=False)
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.packageId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(PackagingTemplates).filter(PackagingTemplates.packageId == data.packageId).first()
    if not entity: return None
    entity.packageName = data.packageName
    entity.state = data.state
    entity.isActive = data.isActive
    entity.userProfileId = data.userProfileId
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.packageId

def delete(db: Session, id_val: int) -> bool:
    entity = db.query(PackagingTemplates).filter(PackagingTemplates.packageId == id_val).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True