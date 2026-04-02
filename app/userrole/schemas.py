from pydantic import BaseModel
from typing import Optional, List, Any

class UserRoleResponse(BaseModel):
    userRoleId: int
    roleName: Optional[str] = None
    isActive: Optional[bool] = None
    class Config:
        from_attributes = True

class UserRoleListResponse(BaseModel):
    count: int
    list: List[UserRoleResponse]
    parameters: Optional[Any] = None