from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from database import Base
from datetime import datetime, timezone


class Email(Base):
    """Stores every sent email as a log record."""
    __tablename__  = "Email"
    __table_args__ = {"schema": "email"}

    EmailId     = Column("EmailId",     Integer,  primary_key=True, autoincrement=True)
    name        = Column("Name",        String,   nullable=True)
    subject     = Column("Subject",     String,   nullable=True)
    email       = Column("Email",       String,   nullable=True)
    message     = Column("Message",     Text,     nullable=True)
    filename    = Column("Filename",    String,   nullable=True)
    isFile      = Column("IsFile",      Boolean,  default=False)
    data        = Column("Data",        Text,     nullable=True)  # JSON string
    isSent      = Column("IsSent",      Boolean,  default=False)
    createdDate = Column("CreatedDate", DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))
    createdBy              = Column("CreatedBy",              String,     nullable=True)
    modifiedBy             = Column("ModifiedBy",             String,     nullable=True)


class EmailCredential(Base):
    """
    Stores SMTP credentials in the database.
    Only one active row is used at a time (isActive = True).
    Admin can add/update credentials from the API without touching .env
    """
    __tablename__  = "EmailCredential"
    __table_args__ = {"schema": "email"}

    EmailCredentialId = Column("EmailCredentialId", Integer, primary_key=True, autoincrement=True)
    smtpHost          = Column("SmtpHost",          String,  nullable=False)
    smtpPort          = Column("SmtpPort",          Integer, nullable=False, default=587)
    smtpUser          = Column("SmtpUser",          String,  nullable=False)
    smtpPassword      = Column("SmtpPassword",      String,  nullable=False)
    displayName       = Column("DisplayName",       String,  nullable=True)   # "From" label in email
    isActive          = Column("IsActive",          Boolean, default=True)
    createdDate       = Column("CreatedDate",       DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc))
    modifiedDate      = Column("ModifiedDate",      DateTime(timezone=True), nullable=True)
    deletedInd        = Column("DeletedInd",        Boolean, default=False)
    createdBy              = Column("CreatedBy",              String,     nullable=True)
    modifiedBy             = Column("ModifiedBy",             String,     nullable=True)