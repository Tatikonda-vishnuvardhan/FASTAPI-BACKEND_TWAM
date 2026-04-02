from sqlalchemy import Column, BigInteger, Boolean, DateTime, Integer, String
from database import Base

class IntegrationLocation(Base):
    __tablename__ = "IntegrationLocation"
    __table_args__ = {"schema": "mdm"}
    integrationLocationId = Column("IntegrationLocationId", BigInteger, primary_key=True, index=True, autoincrement=True)
    locationName = Column("LocationName", String, nullable=True)
    locationType = Column("LocationType", Integer, nullable=True)
    state = Column("State", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)