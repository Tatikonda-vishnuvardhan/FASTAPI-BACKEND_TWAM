from xmlrpc.client import DateTime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = {"schema": "mdm"}

    brandId = Column("brandId", Integer, primary_key=True, index=True)
    brandName = Column("brandName", String, nullable=False)
    brandDescription = Column("brandDescription", String, nullable=True)
    brandImage = Column("brandImage", String, nullable=True)
    brandLogo = Column("brandLogo", String, nullable=True)
    userProfileId = Column("userProfileId", String, nullable=True)
    state = Column("state", String, nullable=True)
    isActive = Column("isActive", Boolean, default=True)
    createdBy = Column("createdBy", String, nullable=True)
    createdDate = Column("createdDate", DateTime(timezone=True))
    modifiedBy = Column("modifiedBy", String, nullable=True)
    modifiedDate = Column("modifiedDate", DateTime(timezone=True)) 
    organizationId = Column("organizationId", String, nullable=True)
    deletedInd = Column(Boolean, default=False)