from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Numeric
from sqlalchemy.sql import func
from database import Base


class Shipment(Base):
    """Maps to shipment.Shipment"""
    __tablename__ = "Shipment"
    __table_args__ = {"schema": "shipment", "extend_existing": True}

    shipmentId          = Column("ShipmentId",          BigInteger, primary_key=True, index=True, autoincrement=True)
    orderId             = Column("OrderId",              BigInteger, nullable=True)
    sellerId            = Column("SellerId",             BigInteger, nullable=True)
    consigneeGSTAmount  = Column("ConsigneeGSTAmount",   Numeric(22, 6), nullable=True)
    orderNumber         = Column("OrderNumber",          String,     nullable=True)
    invoiceNumber       = Column("InvoiceNumber",        String,     nullable=True)
    invoiceDate         = Column("InvoiceDate",          DateTime(timezone=True), nullable=True)
    consigneeName       = Column("ConsigneeName",        String,     nullable=True)
    productDescription  = Column("ProductDescription",   String,     nullable=True)
    paymentMode         = Column("PaymentMode",          String,     nullable=True)
    goodsCategory       = Column("GoodsCategory",        String,     nullable=True)
    totalAmount         = Column("TotalAmount",          Numeric(22, 6), nullable=True)
    taxValue            = Column("TaxValue",             Numeric(22, 6), nullable=True)
    taxableAmount       = Column("TaxableAmount",        Numeric(22, 6), nullable=True)
    commodityValue      = Column("CommodityValue",       String,     nullable=True)
    codAmount           = Column("CODAmount",            Numeric(22, 6), nullable=True)
    quantity            = Column("Quantity",             Integer,    nullable=True)
    weight              = Column("Weight",               Numeric(22, 6), nullable=True)
    length              = Column("Length",               Numeric(22, 6), nullable=True)
    height              = Column("Height",               Numeric(22, 6), nullable=True)
    width               = Column("Width",                Numeric(22, 6), nullable=True)
    pickupAddressId     = Column("PickupAddressId",      BigInteger, nullable=True)
    dropAddressId       = Column("DropAddressId",        BigInteger, nullable=True)
    returnAddressId     = Column("ReturnAddressId",      BigInteger, nullable=True)
    userProfileId       = Column("UserProfileId",        String,     nullable=True)
    state               = Column("State",                String,     nullable=True)
    isSameReturnAddress = Column("IsSameReturnAddress",  Boolean,    nullable=True)
    trackingId          = Column("TrackingId",           String,     nullable=True)
    createdDate         = Column("CreatedDate",          DateTime(timezone=True), server_default=func.now())
    modifiedDate        = Column("ModifiedDate",         DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd          = Column("DeletedInd",           Boolean,    default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)