from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from .models import People

def _get_role(db: Session, role_id):
    if not role_id:
        return None
    try:
        row = db.execute(
            text('SELECT "RoleId", "RoleName" FROM twam."UserRole" WHERE "RoleId" = :id LIMIT 1'),
            {"id": role_id}
        ).fetchone()
        if row:
            return {"roleId": row[0], "roleName": row[1]}
    except Exception:
        pass
    return None


def _to_response(db: Session, p: People) -> dict:
    return {
        "personalId": p.personalId,
        "firstName": p.firstName,
        "middleName": p.middleName,
        "lastName": p.lastName,
        "emailId": p.emailId,
        "phoneNumber": p.phoneNumber,
        "userProfileId": p.userProfileId,
        "isActive": p.isActive,
        "roleId": p.roleId,
        "userRole": _get_role(db, p.roleId),
    }


def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(People).filter(People.deletedInd == False)
    query = apply_filters(query, People, filters)
    query = apply_ordering(query, People, order_property, order_ascending)
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    rows = query.all()
    return build_paged_response(total, [_to_response(db, r) for r in rows])


def get_by_id(db: Session, personal_id: int) -> Optional[dict]:
    entity = db.query(People).filter(People.personalId == personal_id, People.deletedInd == False).first()
    if not entity:
        return None
    return _to_response(db, entity)