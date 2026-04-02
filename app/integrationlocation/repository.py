from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import IntegrationLocation

def _to_dict(r):
    d = {"integrationLocationId": r.integrationLocationId, "createdDate": r.createdDate}
    for attr in ['locationName', 'locationType', 'state', 'isActive', 'userProfileId']:
        v = getattr(r, attr, None)
        d[attr] = float(v) if v is not None and hasattr(v, "__float__") and not isinstance(v, (bool,int,str)) else v
    return d

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(IntegrationLocation).filter(IntegrationLocation.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(IntegrationLocation, f.get("property",""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(IntegrationLocation, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index-1)*page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, id_val: int):
    r = db.query(IntegrationLocation).filter(IntegrationLocation.integrationLocationId == id_val, IntegrationLocation.deletedInd == False).first()
    return _to_dict(r) if r else None

def create(db: Session, data) -> int:
    entity = IntegrationLocation(
        locationName=data.locationName,
        locationType=data.locationType,
        state=data.state,
        isActive=data.isActive,
        userProfileId=data.userProfileId,
        createdDate=datetime.now(timezone.utc), deletedInd=False)
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.integrationLocationId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(IntegrationLocation).filter(IntegrationLocation.integrationLocationId == data.integrationLocationId).first()
    if not entity: return None
    entity.locationName = data.locationName
    entity.locationType = data.locationType
    entity.state = data.state
    entity.isActive = data.isActive
    entity.userProfileId = data.userProfileId
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.integrationLocationId

def delete(db: Session, id_val: int) -> bool:
    entity = db.query(IntegrationLocation).filter(IntegrationLocation.integrationLocationId == id_val).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True