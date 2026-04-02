from sqlalchemy import Column, Integer, BigInteger, Boolean, DateTime, String
from database import Base

class PackagingTemplates(Base):
    __tablename__ = "PackagingTemplates"
    __table_args__ = {"schema": "mdm"}
    packageId = Column("PackageId", BigInteger, primary_key=True, index=True, autoincrement=True)
    packageName = Column("PackageName", String, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)