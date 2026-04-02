from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Numeric, Integer, Text
from sqlalchemy.sql import func
from database import Base


class OrderItems(Base):
    __tablename__ = "OrderItems"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    OrderItemId            = Column("OrderItemId",            BigInteger, primary_key=True, index=True, autoincrement=True)
    OrderId                = Column("OrderId",                BigInteger, nullable=False)
    ProductVariantDetailId = Column("ProductVariantDetailId", BigInteger, nullable=True)
    ProductId              = Column("ProductId",              BigInteger, nullable=True)
    ProductVariantId       = Column("ProductVariantId",       BigInteger, nullable=True)
    OrderItemNumber        = Column("OrderItemNumber",        String,     nullable=True)
    TrackingId             = Column("TrackingId",             String,     nullable=True)
    Quantity               = Column("Quantity",               Integer,    nullable=True)
    Price                  = Column("Price",                  Numeric(22, 6), nullable=True)
    TaxAmount              = Column("TaxAmount",              Numeric(22, 6), nullable=True)
    UnitPrice              = Column("UnitPrice",              Numeric(22, 6), nullable=True)
    CGST                   = Column("CGST",                   Numeric(22, 6), nullable=True)
    SGST                   = Column("SGST",                   Numeric(22, 6), nullable=True)
    Reason                 = Column("Reason",                 Text,       nullable=True)
    IsReturn               = Column("IsReturn",               Boolean,    nullable=True)
    ReferenceOrderItemId   = Column("ReferenceOrderItemId",   BigInteger, nullable=True)
    DeletedInd             = Column("DeletedInd",             Boolean,    default=False, nullable=False)
    CreatedDate            = Column("CreatedDate",            DateTime(timezone=True), server_default=func.now())
    ModifiedDate           = Column("ModifiedDate",           DateTime(timezone=True), onupdate=func.now(), nullable=True)
    CreatedBy              = Column("CreatedBy",              BigInteger, nullable=True)
    ModifiedBy             = Column("ModifiedBy",             BigInteger, nullable=True)