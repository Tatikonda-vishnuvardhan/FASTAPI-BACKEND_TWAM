from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Blog(Base):
    __tablename__ = "Blog"
    __table_args__ = {"schema": "twam"}

    blogId = Column(Integer, primary_key=True, index=True)
    blogContent = Column(Text, nullable=False)
    userProfileId = Column(String, nullable=True)
    state = Column(String, nullable=True)
    isActive = Column(Boolean, default=True)
    blogTitle = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    imageUrl = Column(String, nullable=True)
    deletedInd = Column(Boolean, default=False)
    createdBy = Column(String, nullable=True)
    createdDate = Column(DateTime(timezone=True), server_default=func.now())
    modifiedBy = Column(String, nullable=True)
    modifiedDate = Column(DateTime(timezone=True), onupdate=func.now())
    organizationId = Column(String, nullable=True)