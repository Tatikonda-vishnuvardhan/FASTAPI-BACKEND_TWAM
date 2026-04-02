from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class IntegrationLocationCreate(BaseModel):
    locationName: Optional[str] = None
    locationType: Optional[int] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None

class IntegrationLocationUpdate(BaseModel):
    integrationLocationId: int
    locationName: Optional[str] = None
    locationType: Optional[int] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None

class IntegrationLocationResponse(BaseModel):
    integrationLocationId: int
    locationName: Optional[str] = None
    locationType: Optional[int] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class IntegrationLocationListResponse(BaseModel):
    count: int
    list: List[IntegrationLocationResponse]
    parameters: Optional[Any] = None