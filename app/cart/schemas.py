from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CartCreate(BaseModel):
    productVariantDetailId: Optional[int] = None
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    state: Optional[str] = None
    personalId: Optional[int] = None
    userProfileId: Optional[str] = None
    quantity: Optional[int] = None


class CartItemCommand(BaseModel):
    productVariantDetailId: Optional[int] = None
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    state: Optional[str] = None
    personalId: Optional[int] = None
    quantity: Optional[int] = None


class BulkCartCreate(BaseModel):
    createCartCommands: Optional[List[CartItemCommand]] = None
    userProfileId: Optional[str] = None


class CartUpdate(BaseModel):
    cartId: int
    userProfileId: Optional[str] = None
    productVariantDetailId: Optional[int] = None
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    state: Optional[str] = None
    personalId: Optional[int] = None
    quantity: Optional[int] = None


class CartListItem(BaseModel):
    cartId: int
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    productVariantDetailId: Optional[int] = None
    productCode: Optional[str] = None
    productName: Optional[str] = None
    productDescription: Optional[str] = None
    brandName: Optional[str] = None
    categoryId: Optional[int] = None
    brandId: Optional[int] = None
    variantName: Optional[str] = None
    variantDescription: Optional[str] = None
    size: Optional[str] = None
    cupSize: Optional[str] = None
    color: Optional[str] = None
    stockQuantity: Optional[int] = None
    processedQuantity: Optional[int] = None
    returnedQuantity: Optional[int] = None
    discountPercent: Optional[int] = None
    mrpPrice: Optional[float] = None
    finalPrice: Optional[float] = None
    taxAmount: Optional[float] = None
    personalId: Optional[int] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    image: Optional[str] = None
    quantity: Optional[int] = None
    createdDate: Optional[datetime] = None
    modifiedDate: Optional[datetime] = None

    class Config:
        from_attributes = True


class CartListResponse(BaseModel):
    count: int
    list: List[CartListItem]
    parameters: Optional[Any] = None