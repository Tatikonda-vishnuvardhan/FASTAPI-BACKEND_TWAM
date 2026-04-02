from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ReportListResponse(BaseModel):
    count: int
    list: List[Any]
    parameters: Optional[Any] = None