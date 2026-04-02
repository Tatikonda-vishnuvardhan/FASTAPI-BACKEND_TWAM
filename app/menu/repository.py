from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Menu

def build_menu(menus: list, parent_id) -> list:
    result = []
    for m in [x for x in menus if x["parentMenuId"] == parent_id]:
        item = {**m, "children": build_menu(menus, m["menuId"])}
        result.append(item)
    return result

def get_menu_for_role(db: Session, role_id: int) -> dict:
    # Default to User role (2) if 0
    role_id = role_id if role_id != 0 else 2
    try:
        # Get allowed menu IDs for this role via raw SQL (MenuRoleClaim owned by menurolerlaim module)
        rows = db.execute(text(
            'SELECT DISTINCT "MenuId" FROM twam."MenuRoleClaim" WHERE "RoleId"=:rid AND "DeletedInd"=false'
        ), {"rid": role_id}).fetchall()
        allowed_ids = [r[0] for r in rows]
        if not allowed_ids:
            return {"menus": []}
        menus = db.query(Menu).filter(
            Menu.menuId.in_(allowed_ids),
            Menu.deletedInd == False,
            Menu.isActive == True
        ).order_by(Menu.parentMenuId, Menu.displayOrder).all()
        flat = [{"menuId": m.menuId, "name": m.name, "url": m.url,
                 "parentMenuId": m.parentMenuId, "groupMenuId": m.groupMenuId, "children": []}
                for m in menus]
        return {"menus": build_menu(flat, None)}
    except Exception:
        return {"menus": []}

def get_all_paged(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(Menu).filter(Menu.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(Menu, f.get("property", ""), None)
            if col is not None:
                query = query.filter(col == f.get("value"))
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    rows = query.all()
    result = []
    for m in rows:
        parent_name = None
        if m.parentMenuId:
            try:
                parent = db.query(Menu).filter(Menu.menuId == m.parentMenuId).first()
                parent_name = parent.name if parent else None
            except Exception:
                pass
        result.append({
            "menuId": m.menuId, "name": m.name, "description": m.description,
            "url": m.url, "displayOrder": m.displayOrder, "parentMenuId": m.parentMenuId,
            "groupMenuId": m.groupMenuId, "isActive": m.isActive,
            "state": m.state, "parentMenuName": parent_name
        })
    return {"count": total, "list": result, "parameters": None}

def get_by_id(db: Session, menu_id: int):
    m = db.query(Menu).filter(Menu.menuId == menu_id, Menu.deletedInd == False).first()
    if not m:
        return None
    parent_name = None
    if m.parentMenuId:
        try:
            parent = db.query(Menu).filter(Menu.menuId == m.parentMenuId).first()
            parent_name = parent.name if parent else None
        except Exception:
            pass
    return {
        "menuId": m.menuId, "name": m.name, "description": m.description,
        "url": m.url, "displayOrder": m.displayOrder, "parentMenuId": m.parentMenuId,
        "groupMenuId": m.groupMenuId, "isActive": m.isActive,
        "state": m.state, "parentMenuName": parent_name
    }

def create(db: Session, data) -> int:
    entity = Menu(
        name=data.name, description=data.description, url=data.url,
        displayOrder=data.displayOrder, parentMenuId=data.parentMenuId,
        groupMenuId=data.groupMenuId, isActive=data.isActive, state=data.state,
        createdDate=datetime.now(timezone.utc), deletedInd=False
    )
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.menuId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(Menu).filter(Menu.menuId == data.menuId).first()
    if not entity:
        return None
    entity.name = data.name; entity.description = data.description; entity.url = data.url
    entity.displayOrder = data.displayOrder; entity.parentMenuId = data.parentMenuId
    entity.groupMenuId = data.groupMenuId; entity.isActive = data.isActive; entity.state = data.state
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return entity.menuId

def delete(db: Session, menu_id: int) -> bool:
    entity = db.query(Menu).filter(Menu.menuId == menu_id).first()
    if not entity:
        return False
    entity.deletedInd = True; entity.modifiedDate = datetime.now(timezone.utc)
    db.commit(); return True