from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Numeric, Integer
from database import Base


class Invoice(Base):
    __tablename__ = "Invoice"
    __table_args__ = {"schema": "twam"}

    invoiceId = Column("InvoiceId", BigInteger, primary_key=True, index=True, autoincrement=True)
    orderId = Column("OrderId", BigInteger, nullable=True)
    totalDiscount = Column("TotalDiscount", Numeric(22, 6), nullable=True)
    netBillAmount = Column("NetBillAmount", Numeric(22, 6), nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    invoiceNumber = Column("InvoiceNumber", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)


class InvoiceItem(Base):
    __tablename__ = "InvoiceItem"
    __table_args__ = {"schema": "twam"}

    invoiceItemId = Column("InvoiceItemId", BigInteger, primary_key=True, index=True, autoincrement=True)
    orderId = Column("OrderId", BigInteger, nullable=True)
    orderItemId = Column("OrderItemId", BigInteger, nullable=True)
    productVariantDetailId = Column("ProductVariantDetailId", BigInteger, nullable=True)
    rate = Column("Rate", Numeric(22, 6), nullable=True)
    quantity = Column("Quantity", Integer, nullable=True)
    total = Column("Total", Numeric(22, 6), nullable=True)
    invoiceItemNumber = Column("InvoiceItemNumber", String, nullable=True)