from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class ProductReviewCreate(BaseModel):
    productId:        Optional[int] = None
    productVariantId: Optional[int] = None
    rating:           Optional[int] = None
    comment:          Optional[str] = None
    userProfileId:    Optional[str] = None
    state:            Optional[str] = None
    name:             Optional[str] = None
    email:            Optional[str] = None
    title:            Optional[str] = None
    itemId:           Optional[int] = None
    photo:            Optional[str] = None  # stored URL/path after upload


class ProductReviewUpdate(BaseModel):
    productReviewId:  int
    productId:        Optional[int] = None
    productVariantId: Optional[int] = None
    rating:           Optional[int] = None
    comment:          Optional[str] = None
    userProfileId:    Optional[str] = None
    state:            Optional[str] = None
    name:             Optional[str] = None
    email:            Optional[str] = None
    title:            Optional[str] = None
    itemId:           Optional[int] = None
    photo:            Optional[str] = None  # stored URL/path after upload


class ProductReviewResponse(BaseModel):
    productReviewId:  int
    productId:        Optional[int] = None
    productVariantId: Optional[int] = None
    rating:           Optional[int] = None
    comment:          Optional[str] = None
    name:             Optional[str] = None
    email:            Optional[str] = None
    title:            Optional[str] = None
    userProfileId:    Optional[str] = None
    state:            Optional[str] = None
    itemId:           Optional[int] = None
    photo:            Optional[str] = None  # full URL returned for testimonial display
    createdDate:      Optional[datetime] = None
    modifiedDate:     Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductReviewListResponse(BaseModel):
    count:      int
    list:       List[ProductReviewResponse]
    parameters: Optional[Any] = None


class ProductReviewStatsRequest(BaseModel):
    productId:        Optional[int] = None
    productVariantId: Optional[int] = None


class ProductReviewStatsResponse(BaseModel):
    totalReviews:  int
    averageRating: float
    breakdown:     Dict[int, int] = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
