from sqlalchemy import Column, Integer, BigInteger, Boolean, DateTime, String
from database import Base

class MessageTemplate(Base):
    __tablename__ = "MessageTemplate"
    __table_args__ = {"schema": "mdm"}
    messageTemplateId = Column("MessageTemplateId", BigInteger, primary_key=True, index=True, autoincrement=True)
    messageType = Column("MessageType", String, nullable=True)
    messageContent = Column("MessageContent", String, nullable=True)
    state = Column("State", String, nullable=True)
    dltId = Column("DLTId", String, nullable=True)
    templateId = Column("TemplateId", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)