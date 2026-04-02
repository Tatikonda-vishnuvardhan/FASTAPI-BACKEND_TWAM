from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base


class ProductAudit(Base):
    __tablename__ = "ProductAudit"
    __table_args__ = {"schema": "twam"}

    productAuditId = Column("ProductAuditId", BigInteger, primary_key=True, index=True)
    referenceId = Column("ReferenceId", BigInteger, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    roleId = Column("RoleId", Integer, nullable=True)
    stateName = Column("StateName", String, nullable=True)
    roleName = Column("RoleName", String, nullable=True)
    userName = Column("UserName", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)


class ProductVariantAudit(Base):
    __tablename__ = "ProductVariantAudit"
    __table_args__ = {"schema": "twam"}

    productVariantAuditId = Column("ProductVariantAuditId", BigInteger, primary_key=True, index=True)
    referenceId = Column("ReferenceId", BigInteger, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    roleId = Column("RoleId", Integer, nullable=True)
    stateName = Column("StateName", String, nullable=True)
    roleName = Column("RoleName", String, nullable=True)
    userName = Column("UserName", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)


class ProductVariantDetailAudit(Base):
    __tablename__ = "ProductVariantDetailAudit"
    __table_args__ = {"schema": "twam"}

    productVariantDetailAuditId = Column("ProductVariantDetailAuditId", BigInteger, primary_key=True, index=True)
    referenceId = Column("ReferenceId", BigInteger, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    roleId = Column("RoleId", Integer, nullable=True)
    stateName = Column("StateName", String, nullable=True)
    roleName = Column("RoleName", String, nullable=True)
    userName = Column("UserName", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)