from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class StateCreate(BaseModel):
    stateName: Optional[str] = None
    stateCode: Optional[str] = None
    isActive: bool = True
    countryId: Optional[int] = None
    userProfileId: Optional[str] = None


class StateUpdate(BaseModel):
    stateId: int
    stateName: Optional[str] = None
    stateCode: Optional[str] = None
    isActive: bool = True
    countryId: Optional[int] = None
    userProfileId: Optional[str] = None


class StateResponse(BaseModel):
    stateId: int
    stateName: Optional[str] = None
    stateCode: Optional[str] = None
    isActive: bool
    countryId: Optional[int] = None
    userProfileId: Optional[str] = None

    class Config:
        from_attributes = True


class StateListResponse(BaseModel):
    count: int
    list: List[StateResponse]
    parameters: Optional[Any] = None