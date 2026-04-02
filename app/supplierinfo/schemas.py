from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class SupplierInfoCreate(BaseModel):
    supplierName: Optional[str] = None
    supplierAddress: Optional[str] = None
    supplierGSTNumber: Optional[str] = None
    supplierGSTAmount: Optional[float] = None
    signature: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None

class SupplierInfoUpdate(BaseModel):
    supplierInfoId: int
    supplierName: Optional[str] = None
    supplierAddress: Optional[str] = None
    supplierGSTNumber: Optional[str] = None
    supplierGSTAmount: Optional[float] = None
    signature: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    userProfileId: Optional[str] = None

class SupplierInfoResponse(BaseModel):
    supplierInfoId: int
    supplierName: Optional[str] = None
    supplierAddress: Optional[str] = None
    supplierGSTNumber: Optional[str] = None
    supplierGSTAmount: Optional[float] = None
    signature: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    userProfileId: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class SupplierInfoListResponse(BaseModel):
    count: int
    list: List[SupplierInfoResponse]
    parameters: Optional[Any] = None