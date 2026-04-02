from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import UserRole

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(UserRole).filter(UserRole.deletedInd == False)
    if filters:
        for f in filters:
            prop = f.get("property"); val = f.get("value")
            col = getattr(UserRole, prop, None)
            if col is not None and val is not None:
                query = query.filter(col == val)
    if order_property:
        col = getattr(UserRole, order_property, None)
        if col is not None:
            query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return {"count": total, "list": [{"userRoleId": r.userRoleId, "roleName": r.roleName, "isActive": r.isActive} for r in query.all()], "parameters": None}