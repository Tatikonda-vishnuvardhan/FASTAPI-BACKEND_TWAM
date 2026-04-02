from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Address(Base):
    __tablename__ = "Address"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    addressId       = Column("AddressId",       Integer,    primary_key=True, index=True, autoincrement=True)
    name            = Column("Name",             String,     nullable=True)
    addressLine     = Column("AddressLine",      String,     nullable=True)
    locality        = Column("Locality",         String,     nullable=True)
    city            = Column("City",             String,     nullable=True)
    stateId         = Column("StateId",          BigInteger, nullable=True)
    countryId       = Column("CountryId",        BigInteger, nullable=True)
    pinCode         = Column("PinCode",          String,     nullable=True)
    phone           = Column("Phone",            String,     nullable=True)
    isDefault       = Column("IsDefault",        Boolean,    nullable=True)
    isBillingAddress= Column("IsBillingAddress", Boolean,    nullable=True)
    personalId      = Column("PersonalId",       BigInteger, nullable=False, default=0)
    typeId          = Column("TypeId",           Integer,    nullable=True)
    userProfileId   = Column("UserProfileId",    String,     nullable=True)
    createdDate     = Column("CreatedDate",      DateTime(timezone=True), server_default=func.now())
    modifiedDate    = Column("ModifiedDate",     DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd      = Column("DeletedInd",       Boolean,    default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)