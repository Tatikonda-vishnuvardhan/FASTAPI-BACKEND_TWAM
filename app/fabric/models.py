from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Fabric(Base):
    __tablename__ = "Fabric"
    __table_args__ = {"schema": "mdm", "extend_existing": True}

    fabricId      = Column("FabricId",      BigInteger, primary_key=True, index=True, autoincrement=True)
    name          = Column("Name",           String,     nullable=True)
    fabricCode    = Column("FabricCode",     String,     nullable=True)
    userProfileId = Column("UserProfileId",  String,     nullable=True)
    description   = Column("Description",   String,     nullable=True)
    texture       = Column("Texture",       String,     nullable=True)
    state         = Column("State",         String,     nullable=True)
    isActive      = Column("IsActive",      Boolean,    default=True)
    createdDate   = Column("CreatedDate",   DateTime(timezone=True), server_default=func.now())
    modifiedDate  = Column("ModifiedDate",  DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd    = Column("DeletedInd",    Boolean,    default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)