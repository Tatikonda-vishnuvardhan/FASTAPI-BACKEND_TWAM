from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base


class Size(Base):
    __tablename__ = "Size"
    __table_args__ = {"schema": "mdm"}

    sizeId = Column("SizeId", BigInteger, primary_key=True, index=True)
    sizeLabel = Column("SizeLabel", String, nullable=True)
    sizeCode = Column("SizeCode", String, nullable=True)
    description = Column("Description", String, nullable=True)
    dimensions = Column("Dimensions", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    isCupSize = Column("IsCupSize", Boolean, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    orderNo = Column("OrderNo", Integer, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)