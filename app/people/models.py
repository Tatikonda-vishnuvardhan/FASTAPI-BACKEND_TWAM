from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime
from database import Base


class People(Base):
    __tablename__ = "People"
    __table_args__ = {"schema": "twam"}

    personalId = Column("PersonalId", BigInteger, primary_key=True, index=True, autoincrement=True)
    firstName = Column("FirstName", String, nullable=True)
    middleName = Column("MiddleName", String, nullable=True)
    lastName = Column("LastName", String, nullable=True)
    emailId = Column("EmailId", String, nullable=True)
    phoneNumber = Column("PhoneNumber", String, nullable=True)
    userProfileId = Column("UserProfileId", String, nullable=True)
    isActive = Column("IsActive", Boolean, nullable=True)
    roleId = Column("RoleId", Integer, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)