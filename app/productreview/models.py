from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class ProductReview(Base):
    __tablename__ = "ProductReview"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    productReviewId   = Column("ProductReviewId",   BigInteger, primary_key=True, index=True, autoincrement=True)
    productId         = Column("ProductId",          BigInteger, nullable=True)
    productVariantId  = Column("ProductVariantId",   BigInteger, nullable=True)
    rating            = Column("Rating",             Integer,    nullable=True)
    comment           = Column("Comment",            String,     nullable=True)
    name              = Column("Name",               String,     nullable=True)
    email             = Column("Email",              String,     nullable=True)
    title             = Column("Title",              String,     nullable=True)
    userProfileId     = Column("UserProfileId",      String,     nullable=True)
    state             = Column("State",              String,     nullable=True)
    itemId            = Column("ItemId",             BigInteger, nullable=True)  # FK to OrderItems.OrderItemId
    photo             = Column("Photo",              String,     nullable=True)  # optional user-uploaded photo URL
    createdDate       = Column("CreatedDate",        DateTime(timezone=True), server_default=func.now())
    modifiedDate      = Column("ModifiedDate",       DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd        = Column("DeletedInd",         Boolean,    default=False)
    createdBy         = Column("CreatedBy",          String,     nullable=True)
    modifiedBy        = Column("ModifiedBy",         String,     nullable=True)
    organizationId    = Column("OrganizationId",     Integer,    nullable=True)
