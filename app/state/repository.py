from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from .models import State

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(State).filter(State.deletedInd == False)
    query = apply_filters(query, State, filters)
    query = apply_ordering(query, State, order_property, order_ascending)
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    rows = query.all()
    return {
        "count": total,
        "list": [{"stateId": r.stateId, "stateName": r.stateName, "stateCode": r.stateCode,
                  "isActive": r.isActive, "countryId": r.countryId, "userProfileId": r.userProfileId}
                 for r in rows],
        "parameters": None
    }


def get_by_id(db: Session, state_id: int) -> Optional[dict]:
    entity = db.query(State).filter(State.stateId == state_id, State.deletedInd == False).first()
    if not entity:
        return None
    return {"stateId": entity.stateId, "stateName": entity.stateName, "stateCode": entity.stateCode,
            "isActive": entity.isActive, "countryId": entity.countryId, "userProfileId": entity.userProfileId}


def create(db: Session, data) -> int:
    entity = State(
        stateName=data.stateName,
        stateCode=data.stateCode,
        isActive=data.isActive,
        countryId=data.countryId,
        userProfileId=data.userProfileId,
        createdDate=datetime.now(timezone.utc),
        deletedInd=False,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity.stateId


def update(db: Session, data) -> Optional[int]:
    entity = db.query(State).filter(State.stateId == data.stateId).first()
    if not entity:
        return None
    entity.stateName = data.stateName
    entity.stateCode = data.stateCode
    entity.isActive = data.isActive
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return entity.stateId


def delete(db: Session, state_id: int) -> bool:
    entity = db.query(State).filter(State.stateId == state_id).first()
    if not entity:
        return False
    entity.deletedInd = True
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True