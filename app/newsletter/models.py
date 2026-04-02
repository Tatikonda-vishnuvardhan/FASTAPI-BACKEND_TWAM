from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
from datetime import datetime, timezone


class Newsletter(Base):
    __tablename__  = "Newsletter"
    __table_args__ = {"schema": "twam"}

    NewsletterId   = Column("NewsletterId",   Integer,  primary_key=True, autoincrement=True)
    email          = Column("Email",          String,   nullable=False, unique=True)
    isActive       = Column("IsActive",       Boolean,  default=True)
    createdDate    = Column("CreatedDate",    DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))
    modifiedDate   = Column("ModifiedDate",   DateTime(timezone=True), nullable=True)
    deletedInd     = Column("DeletedInd",     Boolean,  default=False)
    createdBy      = Column("CreatedBy",      String,   nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,   nullable=True)
    organizationId = Column("OrganizationId", Integer,  nullable=True)