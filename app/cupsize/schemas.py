from pydantic import BaseModel
from typing import Optional, List, Any


class CupSizeCreate(BaseModel):
    sizeLabel: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None


class CupSizeUpdate(BaseModel):
    sizeLabel: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None


class CupSizeResponse(BaseModel):
    cupSizeId: int
    sizeLabel: Optional[str] = None
    dimensions: Optional[str] = None
    state: Optional[str] = None
    isActive: bool
    userProfileId: Optional[str] = None
    filters: Optional[Any] = None
    order: Optional[Any] = None
    page: Optional[Any] = None

    class Config:
        from_attributes = True


class CupSizeListResponse(BaseModel):
    count: int
    list: List[CupSizeResponse]
    parameters: Optional[Any] = None