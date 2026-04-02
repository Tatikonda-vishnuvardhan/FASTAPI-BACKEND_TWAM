import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Menu", tags=["Menu"])

# Role-based menu tree for frontend nav
@router.post("/GetMenu", response_model=schemas.MenuResponse)
def get_menu(command: schemas.MenuGetRequest, db: Session = Depends(get_db)):
    return repository.get_menu_for_role(db, command.roleId)

# Admin paged grid
@router.get("/", response_model=schemas.MenuPageListResponse)
def get_grid(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all_paged(db, json.loads(Filters) if Filters else None,
                                    Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.get("/{menu_id}", response_model=schemas.MenuPageResponse)
def get_detail(menu_id: int, db: Session = Depends(get_db)):
    result = repository.get_by_id(db, menu_id)
    if not result: raise HTTPException(404, "Menu not found.")
    return result

@router.post("/", status_code=201)
def create(command: schemas.MenuCreate, db: Session = Depends(get_db)):
    return {"menuId": repository.create(db, command)}

@router.put("/{menu_id}")
def update(menu_id: int, command: schemas.MenuUpdate, db: Session = Depends(get_db)):
    command.menuId = menu_id
    result = repository.update(db, command)
    if not result: raise HTTPException(404, "Menu not found.")
    return {"menuId": result}

@router.delete("/{menu_id}", status_code=204)
def delete(menu_id: int, db: Session = Depends(get_db)):
    if not repository.delete(db, menu_id): raise HTTPException(404, "Menu not found.")