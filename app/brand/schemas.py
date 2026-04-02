from pydantic import BaseModel
from typing import Optional, List, Any


class FilterItem(BaseModel):
    property: str
    comparison: str
    value: str


class BrandResponse(BaseModel):
    brandId: int
    brandName: str
    brandDescription: Optional[str] = None
    brandImage: Optional[str] = None
    brandLogo: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: bool
    filters: Optional[Any] = None
    order: Optional[Any] = None
    page: Optional[Any] = None

    class Config:
        from_attributes = True


class BrandListResponse(BaseModel):
    count: int
    list: List[BrandResponse]
    parameters: Optional[Any] = None


class FileUploadModel(BaseModel):
    fileUploadId: Optional[int] = None
    fileName: Optional[str] = None
    filePath: Optional[str] = None
    fileData: Optional[str] = None
    fileType: Optional[str] = None


class BrandCreate(BaseModel):
    brandId: Optional[int] = None
    brandName: str
    brandDescription: Optional[str] = None
    brandImage: Optional[str] = None
    brandLogo: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    brandLogoFileModel: Optional[FileUploadModel] = None
    brandImageFileModel: Optional[FileUploadModel] = None


class BrandUpdate(BaseModel):
    brandName: Optional[str] = None
    brandDescription: Optional[str] = None
    brandImage: Optional[str] = None
    brandLogo: Optional[str] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isActive: Optional[bool] = None
    brandLogoFileModel: Optional[FileUploadModel] = None
    brandImageFileModel: Optional[FileUploadModel] = None