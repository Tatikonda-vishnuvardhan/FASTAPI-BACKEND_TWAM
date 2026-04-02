from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


# ── JSON element (used in email data payload) ─────────────────────────────────

class JsonElementOptions(BaseModel):
    propertyNameCaseInsensitive: Optional[bool] = None


class JsonElement(BaseModel):
    options: Optional[JsonElementOptions] = None
    parent:  Optional[str] = None
    root:    Optional[str] = None


# ── Email (send + log) ────────────────────────────────────────────────────────

class EmailCreate(BaseModel):
    name:     Optional[str]                    = None
    subject:  Optional[str]                    = None
    email:    Optional[str]                    = None
    message:  Optional[str]                    = None
    filename: Optional[str]                    = None
    isFile:   Optional[bool]                   = None
    data:     Optional[Dict[str, JsonElement]] = None


class EmailResponse(BaseModel):
    EmailId:     int
    name:        Optional[str]      = None
    subject:     Optional[str]      = None
    email:       Optional[str]      = None
    message:     Optional[str]      = None
    isSent:      Optional[bool]     = None
    createdDate: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    count: int
    list:  list[EmailResponse]


# ── EmailCredential ───────────────────────────────────────────────────────────

class EmailCredentialCreate(BaseModel):
    smtpHost:     str
    smtpPort:     Optional[int] = 587
    smtpUser:     str
    smtpPassword: str
    displayName:  Optional[str] = None
    isActive:     Optional[bool] = True


class EmailCredentialUpdate(BaseModel):
    smtpHost:     Optional[str] = None
    smtpPort:     Optional[int] = None
    smtpUser:     Optional[str] = None
    smtpPassword: Optional[str] = None
    displayName:  Optional[str] = None
    isActive:     Optional[bool] = None


class EmailCredentialResponse(BaseModel):
    EmailCredentialId: int
    smtpHost:          str
    smtpPort:          int
    smtpUser:          str
    smtpPassword:      str
    displayName:       Optional[str]      = None
    isActive:          Optional[bool]     = None
    createdDate:       Optional[datetime] = None
    modifiedDate:      Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailCredentialListResponse(BaseModel):
    count: int
    list:  list[EmailCredentialResponse]
