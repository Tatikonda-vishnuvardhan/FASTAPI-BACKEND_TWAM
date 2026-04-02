from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base


class Coupons(Base):
    __tablename__ = "Coupons"
    __table_args__ = {"schema": "twam"}

    couponId = Column("CouponId", BigInteger, primary_key=True, index=True)
    couponCode = Column("CouponCode", String, nullable=True)
    couponName = Column("CouponName", String, nullable=True)
    description = Column("Description", String, nullable=True)
    discount = Column("Discount", Integer, nullable=True)
    startDate = Column("StartDate", DateTime(timezone=True), nullable=True)
    endDate = Column("EndDate", DateTime(timezone=True), nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    isCommon = Column("IsCommon", Boolean, nullable=True)
    toUserProfileId = Column("ToUserProfileId", String, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)