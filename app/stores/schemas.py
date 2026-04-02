from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class StoresCreate(BaseModel):
    storeName: Optional[str] = None
    country: Optional[int] = None
    city: Optional[str] = None
    pinCode: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isPickUpAvailable: Optional[bool] = None
    mapLink: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None

class StoresUpdate(BaseModel):
    storeId: int
    storeName: Optional[str] = None
    country: Optional[int] = None
    city: Optional[str] = None
    pinCode: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isPickUpAvailable: Optional[bool] = None
    mapLink: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True

class StoresResponse(BaseModel):
    storeId: int
    storeName: Optional[str] = None
    country: Optional[int] = None
    countryName: Optional[str] = None
    city: Optional[str] = None
    pinCode: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isPickUpAvailable: Optional[bool] = None
    mapLink: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class StoresListResponse(BaseModel):
    count: int
    list: List[StoresResponse]
    parameters: Optional[Any] = None