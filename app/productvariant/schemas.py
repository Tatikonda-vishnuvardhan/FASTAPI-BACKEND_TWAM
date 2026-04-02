from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Image ─────────────────────────────────────────────────────────────────────

class ImageResponse(BaseModel):
    productImageId:   Optional[int] = None
    fileName:         Optional[str] = None
    filePath:         Optional[str] = None
    fileType:         Optional[str] = None

    class Config:
        from_attributes = True


# ── Create ────────────────────────────────────────────────────────────────────

class ProductVariantCreate(BaseModel):
    productId:          int
    variantName:        Optional[str]  = None
    variantDescription: Optional[str]  = None
    userProfileId:      Optional[str]  = None
    state:              Optional[str]  = None
    productCode:        Optional[str]  = None
    fabricId:           Optional[int]  = None
    color:              Optional[str]  = None
    isBestSeller:       Optional[bool] = None
    isReturnAvailable:  Optional[bool] = None
    isCupSize:          Optional[bool] = None
    taxHSNCodeId:       Optional[int]  = None
    createdBy:          Optional[str]  = None
    modifiedBy:         Optional[str]  = None


# ── Update ────────────────────────────────────────────────────────────────────

class ProductVariantUpdate(BaseModel):
    productId:          Optional[int]  = None
    variantName:        Optional[str]  = None
    variantDescription: Optional[str]  = None
    userProfileId:      Optional[str]  = None
    state:              Optional[str]  = None
    productCode:        Optional[str]  = None
    fabricId:           Optional[int]  = None
    color:              Optional[str]  = None
    isBestSeller:       Optional[bool] = None
    isReturnAvailable:  Optional[bool] = None
    isCupSize:          Optional[bool] = None
    taxHSNCodeId:       Optional[int]  = None
    modifiedBy:         Optional[str]  = None


# ── Response ──────────────────────────────────────────────────────────────────

class ProductVariantResponse(BaseModel):
    productVariantId:   int
    productId:          int
    variantName:        Optional[str]  = None
    variantDescription: Optional[str]  = None
    userProfileId:      Optional[str]  = None
    state:              Optional[str]  = None
    productCode:        Optional[str]  = None
    fabricId:           Optional[int]  = None
    color:              Optional[str]  = None
    isBestSeller:       Optional[bool] = None
    isReturnAvailable:  Optional[bool] = None
    isCupSize:          Optional[bool] = None
    taxHSNCodeId:       Optional[int]  = None
    createdDate:        Optional[datetime] = None
    modifiedDate:       Optional[datetime] = None
    images:             Optional[List[ImageResponse]] = []

    class Config:
        from_attributes = True


class ProductVariantListResponse(BaseModel):
    count:      int
    list:       List[ProductVariantResponse]
    parameters: Optional[Any] = None


# ── User-facing product detail (from GetProductVariantUserListQuery) ───────────

class SizeDetail(BaseModel):
    sizeId:                int
    sizeLabel:             Optional[str] = None
    sizeCode:              Optional[str] = None
    description:           Optional[str] = None
    dimensions:            Optional[str] = None
    productVariantId:      int
    productVariantDetailId: int


class CupSizeDetail(BaseModel):
    cupSizeId:             int
    sizeLabel:             Optional[str] = None
    dimensions:            Optional[str] = None
    productVariantId:      int
    productVariantDetailId: int


class ColorDetail(BaseModel):
    productVariantId: int
    color:            Optional[str] = None
    image:            Optional[str] = None


class UserProductVariantResponse(BaseModel):
    productId:          Optional[int]   = None
    productVariantId:   Optional[int]   = None
    name:               Optional[str]   = None
    brandName:          Optional[str]   = None
    description:        Optional[str]   = None
    productCode:        Optional[str]   = None
    tag:                Optional[str]   = None
    categoryId:         Optional[int]   = None
    isCupSize:          Optional[bool]  = None
    isReturnAvailable:  Optional[bool]  = None
    price:              Optional[float] = None
    originalPrice:      Optional[float] = None
    discountPercentage: Optional[float] = None
    stockQuantity:      Optional[int]   = None
    images:             Optional[List[str]] = []
    sizes:              Optional[List[SizeDetail]] = []
    cupSizes:           Optional[List[CupSizeDetail]] = []
    colors:             Optional[List[ColorDetail]] = []