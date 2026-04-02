from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class MenuCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    displayOrder: Optional[int] = None
    parentMenuId: Optional[int] = None
    groupMenuId: Optional[bool] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None

class MenuUpdate(BaseModel):
    menuId: int
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    displayOrder: Optional[int] = None
    parentMenuId: Optional[int] = None
    groupMenuId: Optional[bool] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None

class MenuItemResponse(BaseModel):
    menuId: int
    name: Optional[str] = None
    url: Optional[str] = None
    parentMenuId: Optional[int] = None
    groupMenuId: Optional[bool] = None
    children: List["MenuItemResponse"] = []

class MenuResponse(BaseModel):
    menus: List[MenuItemResponse]

class MenuPageResponse(BaseModel):
    menuId: int
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    displayOrder: Optional[int] = None
    parentMenuId: Optional[int] = None
    groupMenuId: Optional[bool] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None
    parentMenuName: Optional[str] = None

class MenuPageListResponse(BaseModel):
    count: int
    list: List[MenuPageResponse]
    parameters: Optional[Any] = None

class MenuGetRequest(BaseModel):
    roleId: int = 0