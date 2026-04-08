from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


# ── Create Ekart Shipment ─────────────────────────────────────────────────────

class CreateShipmentRequest(BaseModel):
    orderId:              Optional[int]   = None
    sellerId:             Optional[int]   = None
    consigneeGSTAmount:   Optional[float] = None
    orderNumber:          Optional[str]   = None
    invoiceNumber:        Optional[str]   = None
    invoiceDate:          Optional[datetime] = None
    consigneeName:        Optional[str]   = None
    productDescription:   Optional[str]   = None
    paymentMode:          Optional[str]   = None
    goodsCategory:        Optional[str]   = None
    totalAmount:          Optional[float] = None
    taxValue:             Optional[float] = None
    taxableAmount:        Optional[float] = None
    commodityValue:       Optional[str]   = None
    codAmount:            Optional[float] = None
    quantity:             Optional[int]   = None
    weight:               Optional[float] = None
    length:               Optional[float] = None
    height:               Optional[float] = None
    width:                Optional[float] = None
    pickupAddressId:      Optional[int]   = None
    returnAddressId:      Optional[int]   = None
    isSameReturnAddress:  Optional[bool]  = None
    packagingTemplate:    Optional[str]   = None
    userProfileId:        Optional[str]   = None
    state:                Optional[str]   = None
    # Used as a manual stopgap until Ekart is integrated.
    # Admin can paste the AWB from the Ekart portal here.
    manualTrackingId:     Optional[str]   = None


# ── Create Return Shipment (Ekart) ─────────────────────────────────────────────

class CreateReturnShipmentRequest(CreateShipmentRequest):
    returnShipmentId:   Optional[int] = None
    referenceOrderId:   Optional[int] = None
    returnReason:       Optional[str] = None


# ── Create Delhivery Shipment ─────────────────────────────────────────────────

class CreateDelhiveryShipmentRequest(BaseModel):
    orderId:              Optional[int]   = None
    orderNumber:          Optional[str]   = None
    consigneeName:        Optional[str]   = None
    consigneePhone:       Optional[str]   = None
    consigneeAddress:     Optional[str]   = None
    consigneePinCode:     Optional[str]   = None
    paymentMode:          Optional[str]   = None
    addressType:          Optional[str]   = None
    consigneeCity:        Optional[str]   = None
    consigneeState:       Optional[str]   = None
    hsnCode:              Optional[str]   = None
    shippingMode:         Optional[str]   = None
    invoiceNumber:        Optional[str]   = None
    weight:               Optional[float] = None
    height:               Optional[float] = None
    width:                Optional[float] = None
    length:               Optional[float] = None
    isSameReturnAddress:  Optional[bool]  = None
    returnName:           Optional[str]   = None
    returnAddress:        Optional[str]   = None
    returnCity:           Optional[str]   = None
    returnPhone:          Optional[str]   = None
    returnState:          Optional[str]   = None
    returnCountry:        Optional[str]   = None
    returnPin:            Optional[str]   = None
    sellerId:             Optional[int]   = None
    isFragile:            Optional[bool]  = None
    codAmount:            Optional[float] = None
    productDescription:   Optional[str]   = None
    totalAmount:          Optional[float] = None
    isPlasticPackaging:   Optional[bool]  = None
    quantity:             Optional[int]   = None
    pickupAddressId:      Optional[int]   = None
    userProfileId:        Optional[str]   = None
    state:                Optional[str]   = None


# ── Cancel Shipment ────────────────────────────────────────────────────────────

class CancelShipmentRequest(BaseModel):
    orderId: int


# ── Shipment data queries ─────────────────────────────────────────────────────

class ShipmentDataRequest(BaseModel):
    orderId: int


class ShipmentData(BaseModel):
    consigneeName:      Optional[str]   = None
    orderNumber:        Optional[str]   = None
    invoiceNumber:      Optional[str]   = None
    invoiceDate:        Optional[datetime] = None
    productDescription: Optional[str]   = None
    paymentMode:        Optional[str]   = None
    goodsCategory:      Optional[str]   = None
    totalAmount:        Optional[float] = None
    taxableAmount:      Optional[float] = None
    commodityValue:     Optional[str]   = None
    taxValue:           Optional[float] = None
    quantity:           Optional[int]   = None
    weight:             Optional[float] = None
    codAmount:          Optional[float] = None
    consigneeGSTAmount: Optional[float] = None


class DelhiveryShipmentData(BaseModel):
    orderNumber:        Optional[str]   = None
    consigneeName:      Optional[str]   = None
    consigneePhone:     Optional[str]   = None
    consigneeAddress:   Optional[str]   = None
    consigneePinCode:   Optional[str]   = None
    addressType:        Optional[str]   = None
    consigneeCity:      Optional[str]   = None
    consigneeState:     Optional[str]   = None
    hsnCode:            Optional[str]   = None
    shippingMode:       Optional[str]   = None
    invoiceNumber:      Optional[str]   = None
    weight:             Optional[float] = None
    height:             Optional[float] = None
    width:              Optional[float] = None
    length:             Optional[float] = None
    codAmount:          Optional[float] = None
    productDescription: Optional[str]   = None
    totalAmount:        Optional[float] = None
    quantity:           Optional[int]   = None


class ReturnShipmentData(BaseModel):
    consigneeName:      Optional[str]   = None
    orderNumber:        Optional[str]   = None
    invoiceNumber:      Optional[str]   = None
    invoiceDate:        Optional[datetime] = None
    productDescription: Optional[str]   = None
    paymentMode:        Optional[str]   = None
    goodsCategory:      Optional[str]   = None
    totalAmount:        Optional[float] = None
    taxableAmount:      Optional[float] = None
    commodityValue:     Optional[str]   = None
    taxValue:           Optional[float] = None
    quantity:           Optional[int]   = None
    weight:             Optional[float] = None
    codAmount:          Optional[float] = None
    consigneeGSTAmount: Optional[float] = None
    returnReason:       Optional[str]   = None


# ── Generic shipment response ─────────────────────────────────────────────────

class ShipmentResponse(BaseModel):
    trackingId:  Optional[str] = None
    success:     bool          = False
    message:     Optional[str] = None