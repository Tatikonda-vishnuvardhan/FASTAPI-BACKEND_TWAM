from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class MessageTemplateCreate(BaseModel):
    messageType: Optional[str] = None
    messageContent: Optional[str] = None
    state: Optional[str] = None
    dltId: Optional[str] = None
    templateId: Optional[str] = None

class MessageTemplateUpdate(BaseModel):
    messageTemplateId: int
    messageType: Optional[str] = None
    messageContent: Optional[str] = None
    state: Optional[str] = None
    dltId: Optional[str] = None
    templateId: Optional[str] = None

class MessageTemplateResponse(BaseModel):
    messageTemplateId: int
    messageType: Optional[str] = None
    messageContent: Optional[str] = None
    state: Optional[str] = None
    dltId: Optional[str] = None
    templateId: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class MessageTemplateListResponse(BaseModel):
    count: int
    list: List[MessageTemplateResponse]
    parameters: Optional[Any] = None