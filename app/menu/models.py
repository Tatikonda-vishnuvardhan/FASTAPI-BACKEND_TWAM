from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base

class Menu(Base):
    __tablename__ = "Menu"
    __table_args__ = {"schema": "twam"}
    menuId = Column("MenuId", BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column("Name", String, nullable=True)
    description = Column("Description", String, nullable=True)
    url = Column("Url", String, nullable=True)
    displayOrder = Column("DisplayOrder", Integer, nullable=True)
    parentMenuId = Column("ParentMenuId", BigInteger, nullable=True)
    groupMenuId = Column("GroupMenuId", Boolean, nullable=True)
    isActive = Column("IsActive", Boolean, nullable=True)
    state = Column("State", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)