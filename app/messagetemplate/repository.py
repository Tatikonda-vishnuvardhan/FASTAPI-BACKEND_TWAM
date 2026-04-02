from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import MessageTemplate

def _to_dict(r):
    d = {"messageTemplateId": r.messageTemplateId, "createdDate": r.createdDate}
    for attr in ['messageType', 'messageContent', 'state', 'dltId', 'templateId']:
        v = getattr(r, attr, None)
        d[attr] = float(v) if v is not None and hasattr(v, "__float__") and not isinstance(v, (bool,int,str)) else v
    return d

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(MessageTemplate).filter(MessageTemplate.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(MessageTemplate, f.get("property",""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(MessageTemplate, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index-1)*page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, id_val: int):
    r = db.query(MessageTemplate).filter(MessageTemplate.messageTemplateId == id_val, MessageTemplate.deletedInd == False).first()
    return _to_dict(r) if r else None

def create(db: Session, data) -> int:
    entity = MessageTemplate(
        messageType=data.messageType,
        messageContent=data.messageContent,
        state=data.state,
        dltId=data.dltId,
        templateId=data.templateId,
        createdDate=datetime.now(timezone.utc), deletedInd=False)
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.messageTemplateId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(MessageTemplate).filter(MessageTemplate.messageTemplateId == data.messageTemplateId).first()
    if not entity: return None
    entity.messageType = data.messageType
    entity.messageContent = data.messageContent
    entity.state = data.state
    entity.dltId = data.dltId
    entity.templateId = data.templateId
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.messageTemplateId

def delete(db: Session, id_val: int) -> bool:
    entity = db.query(MessageTemplate).filter(MessageTemplate.messageTemplateId == id_val).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True