from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NewsletterSubscribe(BaseModel):
    email: str


class NewsletterUnsubscribe(BaseModel):
    email: str


class NewsletterBlast(BaseModel):
    subject:   str
    body_html: str
    sent_by:   Optional[str] = None


class NewsletterResponse(BaseModel):
    NewsletterId:   int
    email:          str
    isActive:       bool
    createdDate:    Optional[datetime] = None
    modifiedDate:   Optional[datetime] = None
    organizationId: Optional[int]      = None

    class Config:
        from_attributes = True