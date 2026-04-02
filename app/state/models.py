from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from database import Base


class State(Base):
    __tablename__ = "State"
    __table_args__ = {"schema": "mdm"}

    stateId = Column("StateId", BigInteger, primary_key=True, index=True, autoincrement=True)
    stateName = Column("StateName", String, nullable=True)
    stateCode = Column("StateCode", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    countryId = Column("CountryId", BigInteger, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)