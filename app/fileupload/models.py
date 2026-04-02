from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from database import Base

class FileUpload(Base):
    __tablename__ = "FileUpload"
    __table_args__ = {"schema": "twam"}
    fileUploadId = Column("FileUploadId", BigInteger, primary_key=True, index=True, autoincrement=True)
    fileName = Column("FileName", String, nullable=True)
    filePath = Column("FilePath", String, nullable=True)
    fileType = Column("FileType", String, nullable=True)
    createdDate = Column("CreatedDate", DateTime(timezone=True), nullable=True)
    modifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True)
    deletedInd = Column("DeletedInd", Boolean, default=False)
    createdBy      = Column("CreatedBy",      String,  nullable=True)
    modifiedBy     = Column("ModifiedBy",     String,  nullable=True)
    organizationId = Column("OrganizationId", Integer, nullable=True)