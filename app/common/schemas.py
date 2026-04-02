from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RemarksHistoryResponse(BaseModel):
    stateName: Optional[str] = None
    roleName: Optional[str] = None
    userName: Optional[str] = None
    createdDate: Optional[datetime] = None

    class Config:
        from_attributes = True