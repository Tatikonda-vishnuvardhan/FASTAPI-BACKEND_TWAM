from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class ShippingType(Base):
    __tablename__ = "ShippingType"
    __table_args__ = {"schema": "mdm", "extend_existing": True}

    shippingTypeId   = Column("ShippingTypeId",   BigInteger, primary_key=True, index=True, autoincrement=True)
    shippingTypeName = Column("ShippingTypeName",  String,    nullable=True)
    state            = Column("State",             String,    nullable=True)
    isActive         = Column("IsActive",          Boolean,   default=True)
    userProfileId    = Column("UserProfileId",     String,    nullable=True)
    createdDate      = Column("CreatedDate",       DateTime(timezone=True), server_default=func.now())
    modifiedDate     = Column("ModifiedDate",      DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd       = Column("DeletedInd",        Boolean,   default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)