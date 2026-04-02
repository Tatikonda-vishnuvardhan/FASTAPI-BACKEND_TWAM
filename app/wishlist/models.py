from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from database import Base

class Wishlist(Base):
    __tablename__ = "Wishlist"
    __table_args__ = {"schema": "twam"}
    wishlistId = Column("WishlistId", BigInteger, primary_key=True, index=True, autoincrement=True)
    productId = Column("ProductId", BigInteger, nullable=True)
    productVariantId = Column("ProductVariantId", BigInteger, nullable=True)
    productVariantDetailId = Column("ProductVariantDetailId", BigInteger, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    state = Column("State", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)