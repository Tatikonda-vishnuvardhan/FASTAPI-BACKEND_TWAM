from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Numeric
from database import Base


class Orders(Base):
    __tablename__ = "Orders"
    __table_args__ = {"schema": "twam"}

    orderId = Column("OrderId", BigInteger, primary_key=True, index=True, autoincrement=True)
    totalAmount = Column("TotalAmount", Numeric(22, 6), nullable=True)
    orderDate = Column("OrderDate", DateTime(timezone=True), nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    state = Column("State", String, nullable=True)
    orderNumber = Column("OrderNumber", String, nullable=True)
    shippingAddressId = Column("ShippingAddressId", Integer, nullable=True)
    billingAddressId = Column("BillingAddressId", Integer, nullable=True)
    personalId = Column("PersonalId", BigInteger, nullable=True)
    couponId = Column("CouponId", BigInteger, nullable=True)
    shippingTypeId = Column("ShippingTypeId", BigInteger, nullable=True)
    couponAmount = Column("CouponAmount", Numeric(22, 6), nullable=True)
    deliveryCharge = Column("DeliveryCharge", Numeric(22, 6), nullable=True)
    taxAmount = Column("TaxAmount", Numeric(22, 6), nullable=True)
    subTotal = Column("SubTotal", Numeric(22, 6), nullable=True)
    paymentAccount = Column("PaymentAccount", String, nullable=True)
    paymentTransactionRefNo = Column("PaymentTransactionRefNo", String, nullable=True)
    paymentMethod = Column("PaymentMethod", String, nullable=True)
    orderKeyId = Column("OrderKeyId", String, nullable=True)
    paymentTransactionId = Column("PaymentTransactionId", String, nullable=True)
    deliveryAgent = Column("DeliveryAgent", String, nullable=True)
    isShipped = Column("IsShipped", Boolean, nullable=True)
    reason = Column("Reason", String, nullable=True)
    platform = Column("Platform", String, nullable=True)
    trackingId = Column("TrackingId", String, nullable=True)
    isReturn = Column("IsReturn", Boolean, nullable=True)
    isWhatsappNotification = Column("IsWhatsappNotification", Boolean, nullable=True)
    deliveredDate = Column("DeliveredDate", DateTime(timezone=True), nullable=True)
    referenceOrderId = Column("ReferenceOrderId", BigInteger, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)


class OrderTrackingStatus(Base):
    __tablename__ = "OrderTrackingStatus"
    __table_args__ = {"schema": "twam"}

    trackingStatusId = Column("TrackingId", Integer, primary_key=True, index=True, autoincrement=True)
    orderId = Column("OrderId", BigInteger, nullable=False)
    status = Column("Status", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)


class OrderReturnInfo(Base):
    __tablename__ = "OrderReturnInfo"
    __table_args__ = {"schema": "twam"}

    orderReturnInfoId = Column("OrderReturnInfoId", BigInteger, primary_key=True, index=True, autoincrement=True)
    orderId = Column("OrderId", BigInteger, nullable=False)
    state = Column("State", String, nullable=True)
    reasonId = Column("ReasonId", Integer, nullable=True)
    reason = Column("Reason", String, nullable=True)
    otherReason = Column("OtherReason", String, nullable=True)
    refundChoice = Column("RefundChoice", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)


class OrderRefund(Base):
    __tablename__ = "OrderRefund"
    __table_args__ = {"schema": "payment"}

    orderRefundId = Column("OrderRefundId", BigInteger, primary_key=True, index=True, autoincrement=True)
    orderKeyId = Column("OrderKeyId", String, nullable=True)
    merchanKeyId = Column("MerchanKeyId", Integer, nullable=True)
    uniqueRequestId = Column("UniqueRequestId", String, nullable=True)
    orderId = Column("OrderId", BigInteger, nullable=True)
    orderStatus = Column("OrderStatus", String, nullable=True)
    paymentStatus = Column("PaymentStatus", Integer, nullable=True)
    paymentTransactionId = Column("PaymentTransactionId", String, nullable=True)
    paymentResponseCode = Column("PaymentResponseCode", Integer, nullable=True)
    paymentReasonCode = Column("PaymentReasonCode", String, nullable=True)
    paymentTransactionRefNo = Column("PaymentTransactionRefNo", String, nullable=True)
    paymentMethod = Column("PaymentMethod", String, nullable=True)
    paymentAccount = Column("PaymentAccount", String, nullable=True)
    orderRefundTransactionId = Column("OrderRefundTransactionId", BigInteger, nullable=True)
    refundPaymentResponseCode = Column("RefundPaymentResponseCode", Integer, nullable=True)
    refundPaymentResponseText = Column("RefundPaymentResponseText", String, nullable=True)
    refundDateTime = Column("RefundDateTime", DateTime, nullable=True)
    updatedDateTime = Column("UpdatedDateTime", DateTime, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)