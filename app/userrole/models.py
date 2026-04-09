from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import synonym
from database import Base

class UserRole(Base):
    __tablename__ = "UserRole"
    __table_args__ = {"schema": "twam"}
    UserRoleId = Column("UserRoleId", Integer, primary_key=True, index=True, autoincrement=True)
    RoleName = Column("RoleName", String, nullable=True)
    IsActive = Column("IsActive", Boolean, nullable=True)
    CreatedDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    ModifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    DeletedInd = Column("DeletedInd", Boolean, default=False)
    CreatedBy = Column("CreatedBy", String, nullable=True)
    ModifiedBy = Column("ModifiedBy", String, nullable=True)
    OrganizationId = Column("OrganizationId", Integer, nullable=True)

    # Backward-compatible aliases for existing code that still uses lowercase names.
    userRoleId = synonym("UserRoleId")
    roleName = synonym("RoleName")
    isActive = synonym("IsActive")
    createdDate = synonym("CreatedDate")
    modifiedDate = synonym("ModifiedDate")
    deletedInd = synonym("DeletedInd")
    createdBy = synonym("CreatedBy")
    modifiedBy = synonym("ModifiedBy")
    organizationId = synonym("OrganizationId")
