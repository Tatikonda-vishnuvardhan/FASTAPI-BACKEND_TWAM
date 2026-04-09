"""
Auth Models - IdentityUser and related models
This file was MISSING - causing the auth module to use raw SQL instead of ORM
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base
from app.userrole.models import UserRole

class IdentityUser(Base):
    """
    ASP.NET Core Identity User table
    Schema: auth
    """
    __tablename__ = "IdentityUser"
    __table_args__ = {"schema": "auth"}

    # Primary Identity Fields
    Id = Column("Id", String, primary_key=True, default=lambda: str(uuid.uuid4()))
    UserName = Column("UserName", String, nullable=False)
    NormalizedUserName = Column("NormalizedUserName", String, nullable=False, index=True)
    Email = Column("Email", String, nullable=True)
    NormalizedEmail = Column("NormalizedEmail", String, nullable=True, index=True)
    EmailConfirmed = Column("EmailConfirmed", Boolean, default=False)
    
    # Security Fields
    PasswordHash = Column("PasswordHash", String, nullable=True)
    SecurityStamp = Column("SecurityStamp", String, nullable=True)
    ConcurrencyStamp = Column("ConcurrencyStamp", String, nullable=True)
    
    # Contact Fields
    PhoneNumber = Column("PhoneNumber", String, nullable=True, index=True)
    PhoneNumberConfirmed = Column("PhoneNumberConfirmed", Boolean, default=False)
    
    # Two-Factor & Lockout
    TwoFactorEnabled = Column("TwoFactorEnabled", Boolean, default=False)
    LockoutEnd = Column("LockoutEnd", DateTime(timezone=True), nullable=True)
    LockoutEnabled = Column("LockoutEnabled", Boolean, default=True)
    AccessFailedCount = Column("AccessFailedCount", Integer, default=0)
    
    # User Profile Fields
    FirstName = Column("FirstName", String, nullable=True)
    MiddleName = Column("MiddleName", String, nullable=True)
    LastName = Column("LastName", String, nullable=True)
    
    # Status & Role
    IsActive = Column("IsActive", Boolean, default=True)
    UserRoleId = Column("UserRoleId", Integer, nullable=True)
    
    # Audit Fields
    CreatedDate = Column("CreatedDate", DateTime(timezone=True), default=func.now())
    CreatedBy = Column("CreatedBy", String, nullable=True)
    ModifiedDate = Column("ModifiedDate", DateTime(timezone=True), nullable=True, onupdate=func.now())
    ModifiedBy = Column("ModifiedBy", String, nullable=True)
    
    # Multi-tenancy & Organization
    TenantId = Column("TenantId", String, default="1")
    OrganizationId = Column("OrganizationId", Integer, nullable=True)
    
    # Soft Delete & Password Management
    DeletedInd = Column("DeletedInd", Boolean, default=False)
    IsRandomPassword = Column("IsRandomPassword", Boolean, default=False)

    def __repr__(self):
        return f"<IdentityUser(Id={self.Id}, UserName={self.UserName}, Email={self.Email})>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.FirstName or "", self.MiddleName or "", self.LastName or ""]
        return " ".join(p for p in parts if p).strip()

    def is_locked_out(self) -> bool:
        """Check if user is currently locked out"""
        if not self.LockoutEnabled:
            return False
        if self.LockoutEnd is None:
            return False
        from datetime import datetime, timezone
        return self.LockoutEnd > datetime.now(timezone.utc)

    def should_lock_account(self) -> bool:
        """Check if account should be locked based on failed attempts"""
        return self.AccessFailedCount >= 3

