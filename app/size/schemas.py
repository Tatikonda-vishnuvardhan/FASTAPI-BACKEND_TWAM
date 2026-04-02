from pydantic import BaseModel
from typing import Optional, List, Any


class SizeCreate(BaseModel):
    sizeLabel: Optional[str] = None
    sizeCode: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    isCupSize: Optional[bool] = None
    userProfileId: Optional[str] = None
    orderNo: Optional[int] = None


class SizeUpdate(BaseModel):
    sizeLabel: Optional[str] = None
    sizeCode: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    isCupSize: Optional[bool] = None
    orderNo: Optional[int] = None


class SizeResponse(BaseModel):
    sizeId: int
    sizeLabel: Optional[str] = None
    sizeCode: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: bool
    isCupSize: Optional[bool] = None
    userProfileId: Optional[str] = None
    orderNo: Optional[int] = None
    filters: Optional[Any] = None
    order: Optional[Any] = None
    page: Optional[Any] = None

    class Config:
        from_attributes = True


class SizeListResponse(BaseModel):
    count: int
    list: List[SizeResponse]
    parameters: Optional[Any] = None