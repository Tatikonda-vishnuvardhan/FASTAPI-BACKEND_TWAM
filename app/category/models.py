from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Category(Base):
    __tablename__ = "Category"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    categoryId      = Column("CategoryId",       BigInteger, primary_key=True, index=True, autoincrement=True)
    name            = Column("Name",             String,     nullable=True)
    description     = Column("Description",      String,     nullable=True)
    about           = Column("About",            String,     nullable=True)
    url             = Column("Url",              String,     nullable=True)
    displayOrder    = Column("DisplayOrder",     Integer,    nullable=True)
    parentCategoryId= Column("ParentCategoryId", BigInteger, nullable=True)
    groupCategoryId = Column("GroupCategoryId",  Boolean,    nullable=True)
    isActive        = Column("IsActive",         Boolean,    nullable=True)
    categoryImage   = Column("CategoryImage",    String,     nullable=True)
    createdDate     = Column("CreatedDate",      DateTime(timezone=True), server_default=func.now())
    modifiedDate    = Column("ModifiedDate",     DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd      = Column("DeletedInd",       Boolean,    default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)