from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Numeric
from database import Base


class Cart(Base):
    __tablename__ = "Cart"
    __table_args__ = {"schema": "twam"}

    cartId = Column("CartId", BigInteger, primary_key=True, index=True, autoincrement=True)
    productVariantDetailId = Column("ProductVariantDetailId", BigInteger, nullable=True)
    productId = Column("ProductId", BigInteger, nullable=True)
    productVariantId = Column("ProductVariantId", BigInteger, nullable=True)
    state = Column("State", String, nullable=True)
    personalId = Column("PersonalId", BigInteger, nullable=True)
    isOrdered = Column("IsOrdered", Boolean, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    quantity = Column("Quantity", Integer, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)