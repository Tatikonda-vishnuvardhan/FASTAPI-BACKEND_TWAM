from pydantic import BaseModel
from typing import Optional, List, Any


class CountryCreate(BaseModel):
    countryName: Optional[str] = None
    countryCode: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None
    state: Optional[str] = None


class CountryUpdate(BaseModel):
    countryName: Optional[str] = None
    countryCode: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None


class CountryResponse(BaseModel):
    countryId: int
    countryName: Optional[str] = None
    countryCode: Optional[str] = None
    isActive: bool
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    filters: Optional[Any] = None
    order: Optional[Any] = None
    page: Optional[Any] = None

    class Config:
        from_attributes = True


class CountryListResponse(BaseModel):
    count: int
    list: List[CountryResponse]
    parameters: Optional[Any] = None