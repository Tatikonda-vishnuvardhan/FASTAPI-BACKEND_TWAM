from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class PackagingTemplatesCreate(BaseModel):
    packageName: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None

class PackagingTemplatesUpdate(BaseModel):
    packageId: int
    packageName: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None

class PackagingTemplatesResponse(BaseModel):
    packageId: int
    packageName: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class PackagingTemplatesListResponse(BaseModel):
    count: int
    list: List[PackagingTemplatesResponse]
    parameters: Optional[Any] = None