from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class UserRoleResponse(BaseModel):
    roleId: Optional[int] = None
    roleName: Optional[str] = None


class PeopleResponse(BaseModel):
    personalId: int
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    emailId: Optional[str] = None
    phoneNumber: Optional[str] = None
    userProfileId: Optional[str] = None
    isActive: Optional[bool] = None
    roleId: Optional[int] = None
    userRole: Optional[UserRoleResponse] = None

    class Config:
        from_attributes = True


class PeopleListResponse(BaseModel):
    count: int
    list: List[PeopleResponse]
    parameters: Optional[Any] = None