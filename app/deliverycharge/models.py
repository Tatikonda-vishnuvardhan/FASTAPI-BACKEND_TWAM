from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Numeric
from database import Base


class DeliveryCharge(Base):
    __tablename__ = "DeliveryCharge"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    deliveryChargeId = Column("DeliveryChargeId", BigInteger, primary_key=True, index=True, autoincrement=True)
    shippingTypeId = Column("ShippingTypeId", BigInteger, nullable=True)
    deliveryCharges = Column("DeliveryCharges", Numeric(22, 6), nullable=True)
    orderValueRange = Column("OrderValueRange", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    days = Column("Days", String, nullable=True)
    isFree = Column("IsFree", Boolean, nullable=True)
    description = Column("Description", String, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)