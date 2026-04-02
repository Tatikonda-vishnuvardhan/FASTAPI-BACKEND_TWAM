from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from .models import Stores

def _enrich(db: Session, r: Stores) -> dict:
    country_name = None
    if r.country:
        try:
            row = db.execute(text('SELECT "CountryName" FROM mdm."Country" WHERE "CountryId"=:cid AND "DeletedInd"=false'),
                             {"cid": r.country}).fetchone()
            if row: country_name = row[0]
        except Exception: pass
    return {
        "storeId": r.storeId, "storeName": r.storeName, "country": r.country,
        "countryName": country_name, "city": r.city, "pinCode": r.pinCode,
        "address": r.address, "phone": r.phone, "email": r.email,
        "isPickUpAvailable": r.isPickUpAvailable, "mapLink": r.mapLink,
        "state": r.state, "isActive": r.isActive, "userProfileId": r.userProfileId,
        "createdDate": r.createdDate
    }

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(Stores).filter(Stores.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(Stores, f.get("property", ""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(Stores, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index - 1) * page_size).limit(page_size)
    return {"count": total, "list": [_enrich(db, r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, store_id: int):
    r = db.query(Stores).filter(Stores.storeId == store_id, Stores.deletedInd == False).first()
    return _enrich(db, r) if r else None

def create(db: Session, data) -> int:
    entity = Stores(
        storeName=data.storeName, country=data.country, city=data.city,
        pinCode=data.pinCode, address=data.address, phone=data.phone,
        email=data.email, isPickUpAvailable=data.isPickUpAvailable,
        mapLink=data.mapLink, state=data.state, isActive=data.isActive,
        userProfileId=data.userProfileId, createdDate=datetime.now(timezone.utc), deletedInd=False
    )
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.storeId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(Stores).filter(Stores.storeId == data.storeId).first()
    if not entity: return None
    entity.storeName = data.storeName; entity.country = data.country
    entity.city = data.city; entity.pinCode = data.pinCode; entity.address = data.address
    entity.phone = data.phone; entity.email = data.email
    entity.isPickUpAvailable = data.isPickUpAvailable; entity.mapLink = data.mapLink
    entity.state = data.state; entity.isActive = data.isActive
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.storeId

def delete(db: Session, store_id: int) -> bool:
    entity = db.query(Stores).filter(Stores.storeId == store_id).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True