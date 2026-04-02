from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base

class MenuRoleClaim(Base):
    __tablename__ = "MenuRoleClaim"
    __table_args__ = {"schema": "twam", "extend_existing": True}
    menuRoleClaimId = Column("MenuRoleClaimId", BigInteger, primary_key=True, index=True, autoincrement=True)
    menuId = Column("MenuId", BigInteger, nullable=False)
    roleId = Column("RoleId", Integer, nullable=True)
    isActive = Column("IsActive", Boolean, nullable=True)
    state = Column("State", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)