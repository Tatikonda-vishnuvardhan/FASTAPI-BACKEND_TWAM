from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class ShippingTypeCreate(BaseModel):
    shippingTypeName: Optional[str]  = None
    state:            Optional[str]  = None
    isActive:         bool           = True
    userProfileId:    Optional[str]  = None


class ShippingTypeUpdate(BaseModel):
    shippingTypeName: Optional[str]  = None
    state:            Optional[str]  = None
    isActive:         bool           = True


class ShippingTypeResponse(BaseModel):
    shippingTypeId:   int
    shippingTypeName: Optional[str]  = None
    state:            Optional[str]  = None
    isActive:         bool
    userProfileId:    Optional[str]  = None
    createdDate:      Optional[datetime] = None
    modifiedDate:     Optional[datetime] = None

    class Config:
        from_attributes = True


class ShippingTypeListResponse(BaseModel):
    count:      int
    list:       List[ShippingTypeResponse]
    parameters: Optional[Any] = None