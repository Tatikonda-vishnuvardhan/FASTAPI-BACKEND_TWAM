from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class WishlistCreate(BaseModel):
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    productVariantDetailId: Optional[int] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    isSaveLater: Optional[bool] = None
    cartId: Optional[int] = None

class WishlistItemCommand(BaseModel):
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    productVariantDetailId: Optional[int] = None
    state: Optional[str] = None

class BulkWishlistCreate(BaseModel):
    createWishlistCommands: Optional[List[WishlistItemCommand]] = None
    userProfileId: Optional[str] = None

class WishlistResponse(BaseModel):
    wishlistId: int
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    productVariantDetailId: Optional[int] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    imageURL: Optional[str] = None
    hoverImage: Optional[str] = None
    productName: Optional[str] = None
    variantName: Optional[str] = None
    finalPrice: Optional[float] = None
    mrpPrice: Optional[float] = None
    color: Optional[str] = None
    colorName: Optional[str] = None
    colorHex: Optional[str] = None
    brandName: Optional[str] = None
    rating: Optional[float] = None
    reviewCount: Optional[int] = None
    sizeLabel: Optional[str] = None
    createdDate: Optional[datetime] = None
    class Config:
        from_attributes = True

class WishlistListResponse(BaseModel):
    count: int
    list: List[WishlistResponse]
    parameters: Optional[Any] = None
