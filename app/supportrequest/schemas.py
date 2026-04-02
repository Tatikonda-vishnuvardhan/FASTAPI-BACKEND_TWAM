from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class SupportRequestCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    remarks: Optional[str] = None

class SupportRequestUpdate(BaseModel):
    supportId: int
    name: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    remarks: Optional[str] = None
    state: Optional[str] = None

class SupportRequestResponse(BaseModel):
    supportId: int
    name: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    remarks: Optional[str] = None
    state: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class SupportRequestListResponse(BaseModel):
    count: int
    list: List[SupportRequestResponse]
    parameters: Optional[Any] = None