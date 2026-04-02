from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base

class UserRole(Base):
    __tablename__ = "UserRole"
    __table_args__ = {"schema": "twam"}
    userRoleId = Column("UserRoleId", Integer, primary_key=True, index=True, autoincrement=True)
    roleName = Column("RoleName", String, nullable=True)
    isActive = Column("IsActive", Boolean, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)