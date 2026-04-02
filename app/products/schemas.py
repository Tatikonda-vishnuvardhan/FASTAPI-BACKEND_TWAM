from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Create ────────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    productCode:     Optional[str]  = None
    name:            Optional[str]  = None
    description:     Optional[str]  = None
    categoryId:      Optional[int]  = None
    childCategoryId: Optional[int]  = None
    brandId:         Optional[int]  = None
    personalId:      Optional[int]  = None
    userProfileId:   Optional[str]  = None
    state:           Optional[str]  = None
    tag:             Optional[str]  = None
    createdBy:       Optional[str]  = None
    modifiedBy:      Optional[str]  = None


# ── Update ────────────────────────────────────────────────────────────────────

class ProductUpdate(BaseModel):
    productCode:     Optional[str]  = None
    name:            Optional[str]  = None
    description:     Optional[str]  = None
    categoryId:      Optional[int]  = None
    childCategoryId: Optional[int]  = None
    brandId:         Optional[int]  = None
    personalId:      Optional[int]  = None
    userProfileId:   Optional[str]  = None
    state:           Optional[str]  = None
    tag:             Optional[str]  = None
    modifiedBy:      Optional[str]  = None


# ── Response ──────────────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    productId:       int
    productCode:     Optional[str]  = None
    name:            Optional[str]  = None
    description:     Optional[str]  = None
    categoryId:      Optional[int]  = None
    childCategoryId: Optional[int]  = None
    brandId:         Optional[int]  = None
    personalId:      Optional[int]  = None
    userProfileId:   Optional[str]  = None
    tag:             Optional[str]  = None
    state:           Optional[str]  = None
    createdBy:       Optional[str]  = None
    modifiedBy:      Optional[str]  = None
    createdDate:     Optional[datetime] = None
    modifiedDate:    Optional[datetime] = None
    # Joined field from Brand
    brandName:       Optional[str]  = None

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    count:      int
    list:       List[ProductResponse]
    parameters: Optional[Any] = None


# ── Validation ────────────────────────────────────────────────────────────────

class ProductValidationRequest(BaseModel):
    productId: int
    state:     Optional[str] = None


class ProductValidationResponse(BaseModel):
    isValid: bool