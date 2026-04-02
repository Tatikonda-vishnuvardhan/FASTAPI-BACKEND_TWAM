from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class MenuRoleClaimCreate(BaseModel):
    menuId: int
    roleId: Optional[int] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None

class MenuRoleClaimUpdate(BaseModel):
    menuRoleClaimId: int
    menuId: int
    roleId: Optional[int] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None

class MenuRoleClaimResponse(BaseModel):
    menuRoleClaimId: int
    menuId: int
    roleId: Optional[int] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None
    menuName: Optional[str] = None
    roleName: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class MenuRoleClaimListResponse(BaseModel):
    count: int
    list: List[MenuRoleClaimResponse]
    parameters: Optional[Any] = None