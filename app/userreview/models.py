from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base

class UserReview(Base):
    __tablename__ = "UserReview"
    __table_args__ = {"schema": "twam"}
    userReviewId      = Column("UserReviewId",      BigInteger, primary_key=True, index=True, autoincrement=True)
    productVariantId  = Column("ProductVariantId",  BigInteger, nullable=True)
    rating            = Column("Rating",            Integer,    nullable=True)
    comment           = Column("Comment",           String,     nullable=True)
    userProfileId     = Column("UserProfileId",     String,     nullable=True)
    state             = Column("State",             String,     nullable=True)
    displayName       = Column("DisplayName",       String,     nullable=True)
    email             = Column("Email",             String,     nullable=True)
    reviewTitle       = Column("ReviewTitle",       String,     nullable=True)
    createdDate       = Column("CreatedDate",       DateTime(timezone=True), nullable=True)
    modifiedDate      = Column("ModifiedDate",      DateTime(timezone=True), nullable=True)
    deletedInd        = Column("DeletedInd",        Boolean,    default=False)
    createdBy         = Column("CreatedBy",         String,     nullable=True)
    modifiedBy        = Column("ModifiedBy",        String,     nullable=True)
    organizationId    = Column("OrganizationId",    Integer,    nullable=True)