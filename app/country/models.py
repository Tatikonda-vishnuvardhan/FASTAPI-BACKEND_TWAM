from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from database import Base
from datetime import datetime


class Country(Base):
    __tablename__ = "Country"
    __table_args__ = {"schema": "mdm"}

    countryId = Column("CountryId", BigInteger, primary_key=True, index=True)
    countryName = Column("CountryName", String, nullable=True)
    countryCode = Column("CountryCode", String, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    isActive = Column("IsActive", Boolean, default=True)
    state = Column("State", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), default=datetime.now)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)