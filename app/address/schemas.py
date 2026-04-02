from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class StateResponse(BaseModel):
    stateId:   Optional[int] = None
    stateName: Optional[str] = None

    class Config:
        from_attributes = True


class CountryResponse(BaseModel):
    countryId:   Optional[int] = None
    countryName: Optional[str] = None

    class Config:
        from_attributes = True


class AddressCreate(BaseModel):
    name:             Optional[str]  = None
    addressLine:      Optional[str]  = None
    locality:         Optional[str]  = None
    city:             Optional[str]  = None
    stateId:          Optional[int]  = None
    countryId:        Optional[int]  = None
    pinCode:          Optional[str]  = None
    phone:            Optional[str]  = None
    isDefault:        Optional[bool] = None
    personalId:       int            = 0
    userProfileId:    Optional[str]  = None
    typeId:           Optional[int]  = None
    isBillingAddress: Optional[bool] = None


class AddressUpdate(BaseModel):
    addressId:        int
    name:             Optional[str]  = None
    addressLine:      Optional[str]  = None
    locality:         Optional[str]  = None
    city:             Optional[str]  = None
    stateId:          Optional[int]  = None
    countryId:        Optional[int]  = None
    pinCode:          Optional[str]  = None
    phone:            Optional[str]  = None
    isDefault:        Optional[bool] = None
    personalId:       int            = 0
    userProfileId:    Optional[str]  = None
    typeId:           Optional[int]  = None
    isBillingAddress: Optional[bool] = None


class AddressResponse(BaseModel):
    addressId:        int
    name:             Optional[str]  = None
    addressLine:      Optional[str]  = None
    locality:         Optional[str]  = None
    city:             Optional[str]  = None
    stateId:          Optional[int]  = None
    countryId:        Optional[int]  = None
    pinCode:          Optional[str]  = None
    phone:            Optional[str]  = None
    isDefault:        Optional[bool] = None
    isBillingAddress: Optional[bool] = None
    personalId:       Optional[int]  = None
    typeId:           Optional[int]  = None
    userProfileId:    Optional[str]  = None
    createdDate:      Optional[datetime] = None
    modifiedDate:     Optional[datetime] = None
    # Joined fields
    stateName:        Optional[str]  = None
    countryName:      Optional[str]  = None

    class Config:
        from_attributes = True


class AddressListResponse(BaseModel):
    count:      int
    list:       List[AddressResponse]
    parameters: Optional[Any] = None