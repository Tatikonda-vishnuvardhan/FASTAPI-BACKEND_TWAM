from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CouponCreate(BaseModel):
    couponCode: Optional[str] = None
    couponName: Optional[str] = None
    description: Optional[str] = None
    discount: Optional[int] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    state: Optional[str] = None
    isActive: bool = True
    isCommon: Optional[bool] = None
    toUserProfileId: Optional[str] = None
    userProfileId: Optional[str] = None


class CouponUpdate(BaseModel):
    couponCode: Optional[str] = None
    couponName: Optional[str] = None
    description: Optional[str] = None
    discount: Optional[int] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    isCommon: Optional[bool] = None
    toUserProfileId: Optional[str] = None
    userProfileId: Optional[str] = None


class CouponResponse(BaseModel):
    couponId: int
    couponCode: Optional[str] = None
    couponName: Optional[str] = None
    description: Optional[str] = None
    discount: Optional[int] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    state: Optional[str] = None
    isActive: bool
    isCommon: Optional[bool] = None
    toUserProfileId: Optional[str] = None
    filters: Optional[Any] = None
    order: Optional[Any] = None
    page: Optional[Any] = None

    class Config:
        from_attributes = True


class CouponUserResponse(CouponResponse):
    # Extends CouponResponse with computed IsExpire field
    isExpire: Optional[bool] = None


class CouponListResponse(BaseModel):
    count: int
    list: List[CouponResponse]
    parameters: Optional[Any] = None


class CouponUserListResponse(BaseModel):
    count: int
    list: List[CouponUserResponse]
    parameters: Optional[Any] = None