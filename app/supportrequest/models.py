from sqlalchemy import Column, Integer, BigInteger, Boolean, DateTime, String
from database import Base

class SupportRequest(Base):
    __tablename__ = "SupportRequest"
    __table_args__ = {"schema": "twam"}
    supportId = Column("SupportId", BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column("Name", String, nullable=True)
    email = Column("Email", String, nullable=True)
    subject = Column("Subject", String, nullable=True)
    message = Column("Message", String, nullable=True)
    remarks = Column("Remarks", String, nullable=True)
    state = Column("State", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)