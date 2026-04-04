from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Create ────────────────────────────────────────────────────────────────────

class ProductVariantDetailCreate(BaseModel):
    productId:          int
    productVariantId:   int
    productCode:        Optional[str]   = None
    sizeId:             Optional[int]   = None   # stored in DB column "Size"
    stockQuantity:      Optional[int]   = None
    processedQuantity:  Optional[int]   = None
    returnedQuantity:   Optional[int]   = None
    availableQuantity:  Optional[int]   = None
    discountPercent:    Optional[int]   = None
    mrpPrice:           Optional[float] = None
    finalPrice:         Optional[float] = None
    taxAmount:          Optional[float] = None
    cgst:               Optional[float] = None
    sgst:               Optional[float] = None
    userProfileId:      Optional[str]   = None
    state:              Optional[str]   = None
    cupSizeId:          Optional[int]   = None   # stored in DB column "CupSize"
    stockId:            Optional[str]   = None
    isAlphabetSize:     Optional[bool]  = None
    isLowStock:         Optional[bool]  = None
    isOutOfStock:       Optional[bool]  = None
    createdBy:          Optional[str]   = None
    modifiedBy:         Optional[str]   = None


# ── Update ────────────────────────────────────────────────────────────────────

class ProductVariantDetailUpdate(BaseModel):
    productCode:        Optional[str]   = None
    sizeId:             Optional[int]   = None
    stockQuantity:      Optional[int]   = None
    processedQuantity:  Optional[int]   = None
    returnedQuantity:   Optional[int]   = None
    availableQuantity:  Optional[int]   = None
    amendmentQuantity:  Optional[int]   = None
    discountPercent:    Optional[int]   = None
    mrpPrice:           Optional[float] = None
    finalPrice:         Optional[float] = None
    taxAmount:          Optional[float] = None
    cgst:               Optional[float] = None
    sgst:               Optional[float] = None
    state:              Optional[str]   = None
    cupSizeId:          Optional[int]   = None
    isAlphabetSize:     Optional[bool]  = None
    isLowStock:         Optional[bool]  = None
    isOutOfStock:       Optional[bool]  = None
    # isAmendment controls whether UpdateProductQuantity SP is called in amendment mode
    isAmendment:        Optional[bool]  = None
    modifiedBy:         Optional[str]   = None


# ── Response ──────────────────────────────────────────────────────────────────

class ProductVariantDetailResponse(BaseModel):
    productVariantDetailId: int
    productId:              int
    productVariantId:       int
    productCode:            Optional[str]   = None
    sizeId:                 Optional[int]   = None
    sizeLabel:              Optional[str]   = None   # joined from mdm.Size
    stockQuantity:          Optional[int]   = None
    processedQuantity:      Optional[int]   = None
    returnedQuantity:       Optional[int]   = None
    availableQuantity:      Optional[int]   = None
    amendmentQuantity:      Optional[int]   = None
    discountPercent:        Optional[int]   = None
    mrpPrice:               Optional[float] = None
    finalPrice:             Optional[float] = None
    taxAmount:              Optional[float] = None
    cgst:                   Optional[float] = None
    sgst:                   Optional[float] = None
    userProfileId:          Optional[str]   = None
    state:                  Optional[str]   = None
    stockId:                Optional[str]   = None
    cupSizeId:              Optional[int]   = None
    cupSizeLabel:           Optional[str]   = None   # joined from mdm.CupSize
    isLowStock:             Optional[bool]  = None
    isOutOfStock:           Optional[bool]  = None
    isAlphabetSize:         Optional[bool]  = None
    createdDate:            Optional[datetime] = None
    modifiedDate:           Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductVariantDetailListResponse(BaseModel):
    count:      int
    list:       List[ProductVariantDetailResponse]
    parameters: Optional[Any] = None


# ── Duplicate check ───────────────────────────────────────────────────────────

class CheckVariantDetailRequest(BaseModel):
    productVariantDetailId: Optional[int] = 0   # 0 = new record
    productId:              int
    productVariantId:       int
    sizeId:                 Optional[int] = None
    cupSizeId:              Optional[int] = None


class CheckVariantDetailResponse(BaseModel):
    validationCount: int   # > 0 means duplicate exists


# ── User-facing product detail ────────────────────────────────────────────────

class UserProductDetailResponse(BaseModel):
    productVariantDetailId: Optional[int]   = None
    productId:              Optional[int]   = None
    productVariantId:       Optional[int]   = None
    price:                  Optional[float] = None
    originalPrice:          Optional[float] = None
    discountPercentage:     Optional[float] = None
    stockQuantity:          Optional[int]   = None
    processedQuantity:      Optional[int]   = None


# ── User-facing product list (from SP) ───────────────────────────────────────

class UserProductListItem(BaseModel):
    productVariantId:   Optional[int]   = None
    productId:          Optional[int]   = None
    productCode:        Optional[str]   = None
    fabricId:           Optional[int]   = None
    size:               Optional[Any]   = None
    color:              Optional[str]   = None
    stockQuantity:      Optional[int]   = None
    processedQuantity:  Optional[int]   = None
    discountPercent:    Optional[int]   = None
    mrpPrice:           Optional[float] = None
    finalPrice:         Optional[float] = None
    userProfileId:      Optional[str]   = None
    state:              Optional[str]   = None
    cupSize:            Optional[Any]   = None
    isBestSeller:       Optional[bool]  = None
    totalCount:         Optional[int]   = None
    price:              Optional[float] = None
    oldPrice:           Optional[float] = None
    image:              Optional[str]   = None
    images:             Optional[List[str]] = None   # all variant images for hover crossfade
    name:               Optional[str]   = None
    description:        Optional[str]   = None
    rating:             Optional[float] = None
    reviewCount:        Optional[int]   = None       # review count for rating pill
    brandName:          Optional[str]   = None       # brand display on card


class UserProductListResponse(BaseModel):
    count: int
    list:  List[UserProductListItem]