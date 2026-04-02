from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class FabricCreate(BaseModel):
    name:          Optional[str]  = None
    fabricCode:    Optional[str]  = None
    userProfileId: Optional[str]  = None
    description:   Optional[str]  = None
    texture:       Optional[str]  = None
    state:         Optional[str]  = None
    isActive:      bool           = True


class FabricUpdate(BaseModel):
    name:          Optional[str]  = None
    fabricCode:    Optional[str]  = None
    userProfileId: Optional[str]  = None
    description:   Optional[str]  = None
    texture:       Optional[str]  = None
    state:         Optional[str]  = None
    isActive:      bool           = True


class FabricResponse(BaseModel):
    fabricId:      int
    name:          Optional[str]  = None
    fabricCode:    Optional[str]  = None
    userProfileId: Optional[str]  = None
    description:   Optional[str]  = None
    texture:       Optional[str]  = None
    state:         Optional[str]  = None
    isActive:      bool
    createdDate:   Optional[datetime] = None
    modifiedDate:  Optional[datetime] = None

    class Config:
        from_attributes = True


class FabricListResponse(BaseModel):
    count:      int
    list:       List[FabricResponse]
    parameters: Optional[Any] = None