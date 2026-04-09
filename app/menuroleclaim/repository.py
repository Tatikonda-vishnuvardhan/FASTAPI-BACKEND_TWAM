from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import MenuRoleClaim
from app.menu.models import Menu
from app.userrole.models import UserRole

def _enrich(db: Session, r: MenuRoleClaim) -> dict:
    menu_name = None
    role_name = None
    try:
        menu = db.query(Menu).filter(
            Menu.menuId == r.menuId,
            Menu.deletedInd == False
        ).first()
        if menu:
            menu_name = menu.name
    except Exception: pass
    try:
        role = db.query(UserRole).filter(
            UserRole.UserRoleId == r.roleId,
            UserRole.DeletedInd == False
        ).first()
        if role:
            role_name = role.RoleName
    except Exception: pass
    return {"menuRoleClaimId": r.menuRoleClaimId, "menuId": r.menuId, "roleId": r.roleId,
            "isActive": r.isActive, "state": r.state, "menuName": menu_name,
            "roleName": role_name, "createdDate": r.createdDate}

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(MenuRoleClaim).filter(MenuRoleClaim.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(MenuRoleClaim, f.get("property",""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(MenuRoleClaim, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index-1)*page_size).limit(page_size)
    return {"count": total, "list": [_enrich(db, r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, claim_id: int):
    r = db.query(MenuRoleClaim).filter(MenuRoleClaim.menuRoleClaimId == claim_id, MenuRoleClaim.deletedInd == False).first()
    return _enrich(db, r) if r else None

def create(db: Session, data) -> int:
    entity = MenuRoleClaim(menuId=data.menuId, roleId=data.roleId, isActive=data.isActive,
        state=data.state, createdDate=datetime.now(timezone.utc), deletedInd=False)
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.menuRoleClaimId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(MenuRoleClaim).filter(MenuRoleClaim.menuRoleClaimId == data.menuRoleClaimId).first()
    if not entity: return None
    entity.menuId = data.menuId; entity.roleId = data.roleId
    entity.isActive = data.isActive; entity.state = data.state
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.menuRoleClaimId

def delete(db: Session, claim_id: int) -> bool:
    entity = db.query(MenuRoleClaim).filter(MenuRoleClaim.menuRoleClaimId == claim_id).first()
    if not entity: return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True
