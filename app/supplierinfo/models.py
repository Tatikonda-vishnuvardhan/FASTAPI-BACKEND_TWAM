from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Numeric
from database import Base

class SupplierInfo(Base):
    __tablename__ = "SupplierInfo"
    __table_args__ = {"schema": "mdm"}
    supplierInfoId = Column("SupplierInfoId", BigInteger, primary_key=True, index=True, autoincrement=True)
    supplierName = Column("SupplierName", String, nullable=True)
    supplierAddress = Column("SupplierAddress", String, nullable=True)
    supplierGSTNumber = Column("SupplierGSTNumber", String, nullable=True)
    supplierGSTAmount = Column("SupplierGSTAmount", Numeric(22, 6), nullable=True)
    signature = Column("Signature", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)