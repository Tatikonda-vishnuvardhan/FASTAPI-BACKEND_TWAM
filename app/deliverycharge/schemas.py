from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class ShippingTypeResponse(BaseModel):
    shippingTypeId: Optional[int] = None
    shippingType: Optional[str] = None

    class Config:
        from_attributes = True


class DeliveryChargeCreate(BaseModel):
    shippingTypeId: Optional[int] = None
    deliveryCharges: Optional[float] = None
    orderValueRange: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    days: Optional[str] = None
    isFree: Optional[bool] = None
    description: Optional[str] = None
    userProfileId: Optional[str] = None


class DeliveryChargeUpdate(BaseModel):
    # ── BUG FIX: was `deliveryChargeId: int` (required) — route sets this
    #    from the path param, so it must be Optional here ────────────────────
    deliveryChargeId: Optional[int] = None
    shippingTypeId: Optional[int] = None
    deliveryCharges: Optional[float] = None
    orderValueRange: Optional[str] = None
    state: Optional[str] = None
    isActive: bool = True
    days: Optional[str] = None
    isFree: Optional[bool] = None
    description: Optional[str] = None


class DeliveryChargeResponse(BaseModel):
    deliveryChargeId: int
    shippingTypeId: Optional[int] = None
    deliveryCharges: Optional[float] = None
    orderValueRange: Optional[str] = None
    minOrderValue: Optional[float] = None
    isEligible: Optional[bool] = None
    unlockAmount: Optional[float] = None
    state: Optional[str] = None
    isActive: bool
    days: Optional[str] = None
    isFree: Optional[bool] = None
    description: Optional[str] = None
    userProfileId: Optional[str] = None
    shippingType: Optional[ShippingTypeResponse] = None

    class Config:
        from_attributes = True


class DeliveryChargeListResponse(BaseModel):
    count: int
    list: List[DeliveryChargeResponse]
    parameters: Optional[Any] = None
