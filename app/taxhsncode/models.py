from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Numeric
from database import Base


class TaxHSNCode(Base):
    __tablename__ = "TaxHSNCode"
    __table_args__ = {"schema": "mdm"}

    taxHSNCodeId = Column("TaxHSNCodeId", BigInteger, primary_key=True, index=True, autoincrement=True)
    hsnCode = Column("HSNCode", String, nullable=True)
    hsnDescription = Column("HSNDescription", String, nullable=True)
    cgst = Column("CGST", Numeric(22, 6), nullable=True)
    sgst = Column("SGST", Numeric(22, 6), nullable=True)
    totalGST = Column("TotalGST", Numeric(22, 6), nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)