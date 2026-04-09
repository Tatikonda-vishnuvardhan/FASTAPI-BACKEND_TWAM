from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from .models import People
from app.userrole.models import UserRole

def _get_role(db: Session, role_id):
    if not role_id:
        return None
    try:
        role = db.query(UserRole).filter(
            UserRole.UserRoleId == role_id,
            UserRole.DeletedInd == False
        ).first()
        if role:
            return {"roleId": role.UserRoleId, "roleName": role.RoleName}
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
