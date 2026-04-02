from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ItemsModel(BaseModel):
    sNo: Optional[int] = None
    orderItemId: Optional[int] = None
    description: Optional[str] = None
    unitPrice: Optional[float] = None
    quantity: Optional[int] = None
    netAmount: Optional[float] = None
    taxRate: Optional[float] = None
    taxType: Optional[str] = None
    taxAmount: Optional[float] = None
    totalAmount: Optional[float] = None


class InvoiceResponse(BaseModel):
    orderId: Optional[int] = None
    orderNumber: Optional[str] = None
    orderDate: Optional[datetime] = None
    invoiceNumber: Optional[str] = None
    createdDate: Optional[datetime] = None
    supplierAddress: Optional[str] = None
    supplierName: Optional[str] = None
    supplierGSTNumber: Optional[str] = None
    signature: Optional[str] = None
    panNo: Optional[str] = None
    shippingName: Optional[str] = None
    shippingAddressLine: Optional[str] = None
    shippingCity: Optional[str] = None
    shippingCountryName: Optional[str] = None
    shippingStateName: Optional[str] = None
    shippingPinCode: Optional[str] = None
    shippingPhone: Optional[str] = None
    customerId: Optional[str] = None
    emailAddress: Optional[str] = None
    paymentMethod: Optional[str] = None
    shippingTypeName: Optional[str] = None
    billingName: Optional[str] = None
    billingAddressLine: Optional[str] = None
    billingCity: Optional[str] = None
    billingCountryName: Optional[str] = None
    billingStateName: Optional[str] = None
    billingPinCode: Optional[str] = None
    billingPhone: Optional[str] = None
    taxAmount: Optional[float] = None
    totalAmount: Optional[float] = None
    subTotal: Optional[float] = None
    paymentTransactionRefNo: Optional[str] = None
    itemsModel: Optional[List[ItemsModel]] = None