from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from database import Base


class CupSize(Base):
    __tablename__ = "CupSize"
    __table_args__ = {"schema": "mdm"}

    cupSizeId = Column("CupSizeId", BigInteger, primary_key=True, index=True)
    sizeLabel = Column("SizeLabel", String, nullable=True)
    dimensions = Column("Dimensions", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)