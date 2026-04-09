"""
Auth repository — IMPROVED VERSION using ORM models instead of raw SQL
This replaces the old repository.py that used text() queries everywhere
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from fastapi import HTTPException

from .models import IdentityUser, UserRole
from .security import (
    verify_password, generate_sha256_hash_with_salt,
    _get_password_cipher, _aspnet_hash_password, _decrypt_client_password,
)
from .schemas import RegisterUserRequest

# Setup logger
logger = logging.getLogger(__name__)

PEOPLE_SEQ = 'twam."People_PersonalId_seq"'


# ============================================================================
# HELPER FUNCTIONS - Now using ORM instead of raw SQL
# ============================================================================

def _get_identity_user_by_username(db: Session, username: str) -> Optional[IdentityUser]:
    """
    Find user by username, email, or phone number.
    Uses ORM query instead of raw SQL.
    """
    username_upper = username.upper()
    
    user = db.query(IdentityUser).filter(
        or_(
            IdentityUser.NormalizedUserName == username_upper,
            IdentityUser.PhoneNumber == username,
            IdentityUser.NormalizedEmail == username_upper
        )
    ).first()
    
    return user


def _get_role_name(db: Session, role_id: int) -> str:
    """Get role name from UserRole table using ORM"""
    role = db.query(UserRole).filter(
        UserRole.UserRoleId == role_id
    ).first()
    
    return role.RoleName if role else ""


def _increment_access_failed(db: Session, user: IdentityUser):
    """
    Increment failed access count and lock account if needed.
    Uses ORM instead of raw SQL.
    """
    user.AccessFailedCount += 1
    
    # Lock account after 3 failed attempts
    if user.AccessFailedCount >= 3:
        user.IsActive = False
    
    db.commit()


def _reset_access_failed(db: Session, user: IdentityUser):
    """Reset failed access count using ORM"""
    user.AccessFailedCount = 0
    db.commit()


# ============================================================================
# AUTHENTICATION
# ============================================================================

class AuthResult:
    """Authentication result container"""
    def __init__(self, success: bool, error: str = "", user: IdentityUser = None):
        self.success = success
        self.error = error
        self.user = user


def authenticate_user(db: Session, username: str, encrypted_password: str) -> AuthResult:
    """
    Authenticate user with username and encrypted password.
    IMPROVED: Uses ORM models instead of raw SQL and dictionaries.
    """
    user = _get_identity_user_by_username(db, username)
    
    if not user:
        return AuthResult(False, "not_allowed")
    
    if not user.IsActive:
        return AuthResult(False, "locked_out")
    
    # Verify password
    is_valid = verify_password(
        encrypted_password, 
        user.PasswordHash, 
        is_client_encrypted=True
    )
    
    if not is_valid:
        _increment_access_failed(db, user)
        
        if user.AccessFailedCount >= 3:
            return AuthResult(False, "locked_out")
        
        return AuthResult(False, "invalid_credentials")
    
    # Success - reset failed count
    _reset_access_failed(db, user)
    return AuthResult(True, user=user)


def build_token_claims(db: Session, user: IdentityUser) -> dict:
    """
    Build JWT token claims from user object.
    IMPROVED: Uses ORM model properties instead of dictionary keys.
    """
    role_name = _get_role_name(db, user.UserRoleId or 2)
    session = str(uuid.uuid4())
    
    full_name = user.full_name  # Uses the model property
    
    return {
        "sub": user.Id,
        "preferred_username": user.UserName,
        "name": full_name,
        "sid": session,
        "email": user.Email or "",
        "email_id": user.Email or "",
        "UserId": user.Id,
        "session_id": session,
        "TenantId": user.TenantId or "1",
        "FirstName": user.FirstName or "",
        "MiddleName": user.MiddleName or "",
        "LastName": user.LastName or "",
        "RoleId": str(user.UserRoleId or 2),
        "RoleName": role_name,
        "role": role_name,
        "family_name": user.LastName or "",
        "given_name": user.FirstName or "",
        "phone_number": user.PhoneNumber or "",
    }


# ============================================================================
# USER REGISTRATION
# ============================================================================

def _next_people_id(db: Session) -> Optional[int]:
    """Get next People ID from sequence"""
    try:
        row = db.execute(text(f"SELECT nextval('{PEOPLE_SEQ}')")).fetchone()
        return int(row[0])
    except Exception as e:
        logger.error(f"Sequence error: {e}", exc_info=True)
        return None


def create_identity_user(db: Session, request: RegisterUserRequest) -> dict:
    """
    Create a new user account.
    IMPROVED: Uses ORM model instead of raw INSERT statement.
    """
    try:
        # Check for duplicate phone number
        if request.PhoneNumber:
            existing = db.query(IdentityUser).filter(
                IdentityUser.PhoneNumber == request.PhoneNumber
            ).first()
            
            if existing:
                return {
                    "succeeded": False,
                    "errors": [{
                        "code": "DuplicatePhoneNumber",
                        "description": "Phone number is already taken."
                    }]
                }
        
        # Check for duplicate email
        if request.EmailId:
            normalized_email = request.EmailId.upper()
            existing = db.query(IdentityUser).filter(
                IdentityUser.NormalizedEmail == normalized_email
            ).first()
            
            if existing:
                return {
                    "succeeded": False,
                    "errors": [{
                        "code": "DuplicateEmail",
                        "description": "Email is already taken."
                    }]
                }
        
        # Hash password
        plain_password = request.Password or "Admin@12345"
        twam_hash = generate_sha256_hash_with_salt(plain_password, _get_password_cipher())
        stored_hash = _aspnet_hash_password(twam_hash)
        
        # Create new user using ORM
        new_user = IdentityUser(
            Id=str(uuid.uuid4()),
            UserName=request.EmailId,
            NormalizedUserName=(request.EmailId or "").upper(),
            Email=request.EmailId,
            NormalizedEmail=(request.EmailId or "").upper(),
            EmailConfirmed=True,
            PasswordHash=stored_hash,
            SecurityStamp=str(uuid.uuid4()),
            ConcurrencyStamp=str(uuid.uuid4()),
            PhoneNumber=request.PhoneNumber or "",
            PhoneNumberConfirmed=False,
            TwoFactorEnabled=False,
            LockoutEnabled=True,
            AccessFailedCount=0,
            FirstName=request.FirstName or "",
            MiddleName=request.MiddleName or "",
            LastName=request.LastName or "",
            IsActive=True,
            UserRoleId=request.RoleId if request.RoleId else 2,
            CreatedDate=datetime.now(timezone.utc),
            CreatedBy=request.EmailId,
            TenantId="1",
            OrganizationId=1,
            DeletedInd=False,
            IsRandomPassword=False
        )
        
        db.add(new_user)
        db.flush()  # Get the ID without committing
        
        # Insert into twam.People (still using raw SQL since People model may not exist)
        people_id = _next_people_id(db)
        if people_id:
            db.execute(
                text("""
                    INSERT INTO twam."People"
                    ("PersonalId", "FirstName", "MiddleName", "LastName", "UserProfileId",
                     "RoleId", "EmailId", "PhoneNumber",
                     "IsActive", "CreatedDate", "DeletedInd")
                    VALUES
                    (:pid, :first, :middle, :last, :uid,
                     :role, :email, :phone,
                     true, :now, false)
                """),
                {
                    "pid": people_id,
                    "first": request.FirstName or "",
                    "middle": request.MiddleName or "",
                    "last": request.LastName or "",
                    "uid": new_user.Id,
                    "role": new_user.UserRoleId,
                    "email": request.EmailId or "",
                    "phone": request.PhoneNumber or "",
                    "now": datetime.now(timezone.utc),
                },
            )
        
        db.commit()
        return {
            "succeeded": True,
            "errors": [],
            "user_id": new_user.Id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

def reset_password_with_token(db: Session, email: str, new_password: str) -> dict:
    """
    Reset password after token validation.
    IMPROVED: Uses ORM model instead of raw UPDATE.
    """
    try:
        user = _get_identity_user_by_username(db, email)
        
        if not user:
            return {
                "succeeded": False,
                "errors": [{
                    "code": "NotFound",
                    "description": "User not found."
                }]
            }
        
        # Decrypt password
        try:
            new_plain = _decrypt_client_password(new_password)
        except Exception:
            # If decryption fails, treat as plain text
            new_plain = new_password
        
        # Hash the new password
        new_twam = generate_sha256_hash_with_salt(new_plain, _get_password_cipher())
        new_db_hash = _aspnet_hash_password(new_twam)
        
        # Update user using ORM
        user.PasswordHash = new_db_hash
        user.SecurityStamp = str(uuid.uuid4())
        user.ModifiedDate = datetime.now(timezone.utc)
        user.ModifiedBy = email
        user.AccessFailedCount = 0
        user.IsActive = True
        
        db.commit()
        return {"succeeded": True, "errors": []}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset password: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset password: {str(e)}"
        )


def change_password(db: Session, email_id: str, current_password: str, new_password: str) -> dict:
    """
    Change password with current password verification.
    IMPROVED: Uses ORM model instead of raw UPDATE.
    """
    try:
        user = _get_identity_user_by_username(db, email_id)
        
        if not user:
            return {
                "succeeded": False,
                "errors": [{
                    "code": "NotFound",
                    "description": "User not found."
                }]
            }
        
        # Verify current password
        if not verify_password(current_password, user.PasswordHash, is_client_encrypted=True):
            return {
                "succeeded": False,
                "errors": [{
                    "code": "PasswordMismatch",
                    "description": "Current password is incorrect."
                }]
            }
        
        # Decrypt and hash new password
        new_plain = _decrypt_client_password(new_password)
        new_twam = generate_sha256_hash_with_salt(new_plain, _get_password_cipher())
        new_db_hash = _aspnet_hash_password(new_twam)
        
        # Update using ORM
        user.PasswordHash = new_db_hash
        user.SecurityStamp = str(uuid.uuid4())
        user.ModifiedDate = datetime.now(timezone.utc)
        user.ModifiedBy = email_id
        
        db.commit()
        return {"succeeded": True, "errors": []}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to change password: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to change password: {str(e)}"
        )


# ============================================================================
# ADDITIONAL HELPFUL FUNCTIONS
# ============================================================================

def get_user_by_id(db: Session, user_id: str) -> Optional[IdentityUser]:
    """Get user by ID using ORM"""
    return db.query(IdentityUser).filter(
        IdentityUser.Id == user_id,
        IdentityUser.DeletedInd == False
    ).first()


def get_user_by_email(db: Session, email: str) -> Optional[IdentityUser]:
    """Get user by email using ORM"""
    return db.query(IdentityUser).filter(
        IdentityUser.NormalizedEmail == email.upper(),
        IdentityUser.DeletedInd == False
    ).first()


def deactivate_user(db: Session, user_id: str) -> bool:
    """Soft delete/deactivate user"""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.IsActive = False
        user.DeletedInd = True
        user.ModifiedDate = datetime.now(timezone.utc)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deactivate user: {str(e)}", exc_info=True)
        return False