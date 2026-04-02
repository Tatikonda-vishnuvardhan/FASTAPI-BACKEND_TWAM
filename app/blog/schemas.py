from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BlogBase(BaseModel):
    blogTitle: str
    blogContent: str
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    state: Optional[str] = None
    userProfileId: Optional[str] = None
    organizationId: Optional[str] = None


class BlogCreate(BlogBase):
    pass


class BlogUpdate(BaseModel):
    blogTitle: str
    blogContent: str
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    state: Optional[str] = None
    userProfileId: Optional[str] = None
    organizationId: Optional[str] = None
    isActive: bool
    deletedInd: bool
    createdBy: Optional[str] = None
    modifiedBy: Optional[str] = None


class BlogResponse(BaseModel):
    blogId: int
    blogTitle: str
    blogContent: str
    description: Optional[str]
    imageUrl: Optional[str]
    state: Optional[str]
    userProfileId: Optional[str]
    organizationId: Optional[str]
    isActive: bool
    deletedInd: bool
    createdBy: Optional[str]
    createdDate: datetime
    modifiedBy: Optional[str]
    modifiedDate: Optional[datetime]

    class Config:
        from_attributes = True


class BlogListResponse(BaseModel):
    count: int
    list: List[BlogResponse]
    parameters: dict


class BlogWrappedResponse(BaseModel):
    success: bool
    message: str
    data: BlogResponse