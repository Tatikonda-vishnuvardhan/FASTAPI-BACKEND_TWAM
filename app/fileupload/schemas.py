from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class FileUploadCreate(BaseModel):
    fileName: Optional[str] = None
    filePath: Optional[str] = None
    fileData: Optional[str] = None   # base64 encoded file content
    fileType: Optional[str] = None

class FileUploadResponse(BaseModel):
    fileUploadId: int
    fileName: Optional[str] = None
    filePath: Optional[str] = None
    fileType: Optional[str] = None
    fileUrl: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class FileUploadListResponse(BaseModel):
    count: int
    list: List[FileUploadResponse]
    parameters: Optional[Any] = None