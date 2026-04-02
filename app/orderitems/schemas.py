from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# ──────────────────────────────────────────────
# Grid / Pagination helpers
# ──────────────────────────────────────────────

class PageParams(BaseModel):
    pageNumber: Optional[int] = 1
    pageSize:   Optional[int] = 10


class FilterParam(BaseModel):
    field:    Optional[str] = None
    operator: Optional[str] = None   # eq, neq, contains, gt, lt, gte, lte
    value:    Optional[str] = None


class OrderParam(BaseModel):
    field:     Optional[str] = None
    direction: Optional[str] = "asc"  # asc | desc


class GridParameters(BaseModel):
    page:    Optional[PageParams]          = None
    filters: Optional[List[FilterParam]]   = None
    order:   Optional[OrderParam]          = None


# ──────────────────────────────────────────────
# OrderItem response schemas
# ──────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    OrderItemId:            int
    OrderId:                int
    ProductVariantDetailId: Optional[int]     = None
    ProductId:              Optional[int]     = None
    ProductVariantId:       Optional[int]     = None
    OrderItemNumber:        Optional[str]     = None
    TrackingId:             Optional[str]     = None
    Quantity:               Optional[int]     = None
    Price:                  Optional[Decimal] = None
    TaxAmount:              Optional[Decimal] = None
    UnitPrice:              Optional[Decimal] = None
    CGST:                   Optional[Decimal] = None
    SGST:                   Optional[Decimal] = None
    Reason:                 Optional[str]     = None
    IsReturn:               Optional[bool]    = None
    ReferenceOrderItemId:   Optional[int]     = None
    DeletedInd:             Optional[bool]    = False
    CreatedDate:            Optional[datetime] = None
    ModifiedDate:           Optional[datetime] = None

    # Joined / computed fields
    product_name:           Optional[str]     = None
    size_label:             Optional[str]     = None
    cup_size_label:         Optional[str]     = None
    color:                  Optional[str]     = None
    variant_name:           Optional[str]     = None
    is_return_available:    Optional[bool]    = None
    Image:                  Optional[str]     = None


class OrderItemCreate(BaseModel):
    OrderId:                int
    ProductVariantDetailId: Optional[int]     = None
    ProductId:              Optional[int]     = None
    ProductVariantId:       Optional[int]     = None
    OrderItemNumber:        Optional[str]     = None
    TrackingId:             Optional[str]     = None
    Quantity:               Optional[int]     = None
    Price:                  Optional[Decimal] = None
    TaxAmount:              Optional[Decimal] = None
    UnitPrice:              Optional[Decimal] = None
    CGST:                   Optional[Decimal] = None
    SGST:                   Optional[Decimal] = None
    Reason:                 Optional[str]     = None
    IsReturn:               Optional[bool]    = None
    ReferenceOrderItemId:   Optional[int]     = None


class OrderItemUpdate(BaseModel):
    ProductVariantDetailId: Optional[int]     = None
    ProductId:              Optional[int]     = None
    ProductVariantId:       Optional[int]     = None
    OrderItemNumber:        Optional[str]     = None
    TrackingId:             Optional[str]     = None
    Quantity:               Optional[int]     = None
    Price:                  Optional[Decimal] = None
    TaxAmount:              Optional[Decimal] = None
    UnitPrice:              Optional[Decimal] = None
    CGST:                   Optional[Decimal] = None
    SGST:                   Optional[Decimal] = None
    Reason:                 Optional[str]     = None
    IsReturn:               Optional[bool]    = None
    ReferenceOrderItemId:   Optional[int]     = None


# ──────────────────────────────────────────────
# Paginated Grid response wrapper
# ──────────────────────────────────────────────

class OrderItemGrid(BaseModel):
    total:      int
    page:       int
    page_size:  int
    items:      List[OrderItemResponse]