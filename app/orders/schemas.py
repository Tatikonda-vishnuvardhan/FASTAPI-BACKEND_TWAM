from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Shared ──────────────────────────────────────────────────────────────────

class OrderItemInput(BaseModel):
    productVariantDetailId: Optional[int] = None
    productVariantId: Optional[int] = None
    productId: Optional[int] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    taxAmount: Optional[float] = None


class OutOfStockResult(BaseModel):
    productVariantDetailId: int
    stockQuantity: Optional[int] = None
    productName: Optional[str] = None


class OrderResponse(BaseModel):
    orderId: Optional[int] = None
    paymentProcessUrl: Optional[str] = None
    outOfStockProducts: Optional[List[OutOfStockResult]] = None
    isPhoneNumber: Optional[bool] = None
    isEmailDuplicate: Optional[bool] = None


# ── Create Order ─────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    totalAmount: Optional[float] = None
    orderDate: Optional[datetime] = None
    userProfileId: Optional[str] = None
    shippingAddressId: Optional[int] = None
    billingAddressId: Optional[int] = None
    couponId: Optional[int] = None
    shippingTypeId: Optional[int] = None
    couponAmount: Optional[float] = None
    deliveryCharge: Optional[float] = None
    taxAmount: Optional[float] = None
    subTotal: Optional[float] = None
    cartId: Optional[List[int]] = None
    orderItems: Optional[List[OrderItemInput]] = None
    isWhatsappNotification: Optional[bool] = None


# ── ReOrder (Cart) ────────────────────────────────────────────────────────────

class CreateOrderCartRequest(BaseModel):
    orderId: int
    userProfileId: Optional[str] = None


# ── Guest Order ───────────────────────────────────────────────────────────────

class CreateGuestOrderRequest(BaseModel):
    totalAmount: Optional[float] = None
    orderDate: Optional[datetime] = None
    shippingTypeId: Optional[int] = None
    couponId: Optional[int] = None
    couponAmount: Optional[float] = None
    deliveryCharge: Optional[float] = None
    taxAmount: Optional[float] = None
    subTotal: Optional[float] = None
    # Guest personal info
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    # Address
    addressLine: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    stateId: Optional[int] = None
    pinCode: Optional[str] = None
    countryId: Optional[int] = None
    isDefault: Optional[bool] = None
    isBillingAddress: Optional[bool] = None
    typeId: Optional[int] = None
    orderItems: Optional[List[OrderItemInput]] = None
    isWhatsappNotification: Optional[bool] = None


# ── Return Order ──────────────────────────────────────────────────────────────

class ReturnOrderItemInput(BaseModel):
    orderItemId: int
    quantity: Optional[int] = None
    price: Optional[float] = None


class CreateReturnOrderRequest(BaseModel):
    orderId: int
    orderItems: Optional[List[ReturnOrderItemInput]] = None
    reasonId: Optional[int] = None
    reason: Optional[str] = None
    otherReason: Optional[str] = None
    shippingOption: Optional[str] = None


# ── Cancel Order ──────────────────────────────────────────────────────────────

class CancelOrderRequest(BaseModel):
    orderId: int
    isRefund: bool = False
    reason: Optional[str] = None
    platform: Optional[str] = None


# ── OutOfStock Validation ─────────────────────────────────────────────────────

class CheckOutOfStockRequest(BaseModel):
    orderItems: Optional[List[OrderItemInput]] = None


class ValidationResponse(BaseModel):
    outOfStockProducts: Optional[List[OutOfStockResult]] = None


# ── Order List ────────────────────────────────────────────────────────────────

class OrderItemModel(BaseModel):
    orderItemId: int
    orderId: int
    productVariantDetailId: Optional[int] = None
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    productName: Optional[str] = None
    productImage: Optional[str] = None
    size: Optional[str] = None
    cupSize: Optional[str] = None
    color: Optional[str] = None
    orderItemNumber: Optional[str] = None
    subTotal: Optional[float] = None
    isReturnAvailable: Optional[bool] = None
    rating: Optional[int] = None
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class DeliveryInfoResponse(BaseModel):
    deliveryChargeId: Optional[int] = None
    deliveryCharges: Optional[float] = None
    days: Optional[str] = None
    isFree: Optional[bool] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AddressResponse(BaseModel):
    addressId: Optional[int] = None
    addressLine: Optional[str] = None
    city: Optional[str] = None
    pinCode: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None

    class Config:
        from_attributes = True


class GetOrderListItem(BaseModel):
    orderId: int
    totalAmount: Optional[float] = None
    orderDate: Optional[datetime] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    orderNumber: Optional[str] = None
    shippingAddressId: Optional[int] = None
    paymentAccount: Optional[str] = None
    paymentTransactionRefNo: Optional[str] = None
    couponAmount: Optional[float] = None
    deliveryCharge: Optional[float] = None
    taxAmount: Optional[float] = None
    subTotal: Optional[float] = None
    isShipped: Optional[bool] = None
    reason: Optional[str] = None
    deliveredDate: Optional[datetime] = None
    address: Optional[AddressResponse] = None
    deliveryInfo: Optional[DeliveryInfoResponse] = None
    orderItems: Optional[List[OrderItemModel]] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    count: Optional[int] = None
    list: Optional[List[GetOrderListItem]] = None
    parameters: Optional[Any] = None


# ── Order Admin List ──────────────────────────────────────────────────────────

class OrderAdminItemModel(BaseModel):
    orderItemId: int
    orderId: int
    productVariantDetailId: Optional[int] = None
    productId: Optional[int] = None
    productVariantId: Optional[int] = None
    quantity: Optional[int] = None
    totalItems: Optional[int] = None
    totalQuantity: Optional[int] = None
    price: Optional[float] = None
    productName: Optional[str] = None
    productImage: Optional[str] = None
    size: Optional[str] = None
    cupSize: Optional[str] = None
    color: Optional[str] = None
    orderItemNumber: Optional[str] = None

    class Config:
        from_attributes = True


class GetAdminOrderListItem(BaseModel):
    orderId: int
    totalAmount: Optional[float] = None
    orderDate: Optional[datetime] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    orderNumber: Optional[str] = None
    shippingAddressId: Optional[int] = None
    paymentAccount: Optional[str] = None
    paymentTransactionRefNo: Optional[str] = None
    couponAmount: Optional[float] = None
    deliveryCharge: Optional[float] = None
    taxAmount: Optional[float] = None
    subTotal: Optional[float] = None
    reason: Optional[str] = None
    deliveryAgent: Optional[str] = None
    referenceOrderId: Optional[int] = None
    address: Optional[AddressResponse] = None
    orderItems: Optional[List[OrderAdminItemModel]] = None

    class Config:
        from_attributes = True


class AdminOrderListResponse(BaseModel):
    count: Optional[int] = None
    list: Optional[List[GetAdminOrderListItem]] = None
    parameters: Optional[Any] = None


# ── Order Details ─────────────────────────────────────────────────────────────

class GetOrderDetailsResponse(BaseModel):
    orderId: int
    totalAmount: Optional[float] = None
    orderDate: Optional[datetime] = None
    userProfileId: Optional[str] = None
    state: Optional[str] = None
    orderNumber: Optional[str] = None
    shippingAddressId: Optional[int] = None
    billingAddressId: Optional[int] = None
    paymentStatus: Optional[int] = None
    paymentTransactionRefNo: Optional[str] = None
    paymentAccount: Optional[str] = None
    paymentReasonCode: Optional[str] = None
    subTotal: Optional[float] = None
    taxAmount: Optional[float] = None
    deliveryCharge: Optional[float] = None
    shippingAddress: Optional[AddressResponse] = None
    billingAddress: Optional[AddressResponse] = None
    deliveryInfo: Optional[DeliveryInfoResponse] = None
    orderItems: Optional[List[OrderItemModel]] = None

    class Config:
        from_attributes = True


# ── Order Tracking ────────────────────────────────────────────────────────────

class OrderTimelineStep(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None


class OrderTrackingResponse(BaseModel):
    steps: Optional[List[OrderTimelineStep]] = None


# ── Return Order Items ────────────────────────────────────────────────────────

class ReturnOrderItem(BaseModel):
    orderItemId: int
    productName: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    productImage: Optional[str] = None
    isReturnable: Optional[bool] = None
    isReturnExpired: Optional[bool] = None
    returnExpiryDate: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReturnOrderDetails(BaseModel):
    orderId: int
    orderNumber: Optional[str] = None
    orderDate: Optional[datetime] = None
    orderItems: Optional[List[ReturnOrderItem]] = None


class ReturnOrderItemsResponse(BaseModel):
    count: Optional[int] = None
    list: Optional[List[ReturnOrderDetails]] = None
    parameters: Optional[Any] = None