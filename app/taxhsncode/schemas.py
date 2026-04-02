from pydantic import BaseModel
from typing import Optional, List, Any


class TaxHSNCodeCreate(BaseModel):
    hsnCode: Optional[str] = None
    hsnDescription: Optional[str] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    totalGST: Optional[float] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True


class TaxHSNCodeUpdate(BaseModel):
    taxHSNCodeId: int
    hsnCode: Optional[str] = None
    hsnDescription: Optional[str] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    totalGST: Optional[float] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True


class TaxHSNCodeResponse(BaseModel):
    taxHSNCodeId: int
    hsnCode: Optional[str] = None
    hsnDescription: Optional[str] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    totalGST: Optional[float] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: bool

    class Config:
        from_attributes = True


class TaxHSNCodeListResponse(BaseModel):
    count: int
    list: List[TaxHSNCodeResponse]
    parameters: Optional[Any] = None