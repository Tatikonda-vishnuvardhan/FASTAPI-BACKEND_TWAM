from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class UserReviewCreate(BaseModel):
    productVariantId: Optional[int] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    displayName: Optional[str] = None
    email: Optional[str] = None
    reviewTitle: Optional[str] = None

class UserReviewUpdate(BaseModel):
    userReviewId: int
    productVariantId: Optional[int] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    displayName: Optional[str] = None
    email: Optional[str] = None
    reviewTitle: Optional[str] = None

class UserReviewResponse(BaseModel):
    userReviewId: int
    productVariantId: Optional[int] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    displayName: Optional[str] = None
    email: Optional[str] = None
    reviewTitle: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class UserReviewListResponse(BaseModel):
    count: int
    list: List[UserReviewResponse]
    parameters: Optional[Any] = None