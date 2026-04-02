from pydantic import BaseModel
from typing import Optional, List

class BestSellerProduct(BaseModel):
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    oldPrice: Optional[float] = None
    image: Optional[str] = None
    bestseller: Optional[bool] = None
    color: Optional[str] = None
    rating: Optional[float] = None

class WishlistItem(BaseModel):
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    productVariantDetailId: Optional[int] = None

class UserDashboardRequest(BaseModel):
    userProfileId: Optional[str] = None

class UserDashboardResponse(BaseModel):
    cartCount: int = 0
    wishlistCount: int = 0
    bestSellers: List[BestSellerProduct] = []
    newArrivals: List[BestSellerProduct] = []
    wishlistItems: List[WishlistItem] = []