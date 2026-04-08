"""
Auth repository — updated with full IdentityUser column set.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from .security import (
    verify_password, generate_sha256_hash_with_salt,
    _get_password_cipher, _aspnet_hash_password, _decrypt_client_password,
)
from .schemas import RegisterUserRequest

IDENTITY_USER_TABLE = 'auth."IdentityUser"'
PEOPLE_SEQ          = 'twam."People_PersonalId_seq"'


def _get_identity_user_by_username(db: Session, username: str) -> Optional[dict]:
    row = db.execute(
        text(f"""
            SELECT "Id", "UserName", "Email", "PasswordHash",
                   "FirstName", "MiddleName", "LastName",
                   "PhoneNumber", "IsActive", "UserRoleId",
                   "AccessFailedCount"
            FROM {IDENTITY_USER_TABLE}
            WHERE "NormalizedUserName" = :uname
               OR "PhoneNumber"        = :uname
            LIMIT 1
        """),
        {"uname": username.upper()},
    ).fetchone()

    if not row:
        return None

    return {
        "id":                  row[0],
        "user_name":           row[1],
        "email":               row[2],
        "password_hash":       row[3],
        "first_name":          row[4] or "",
        "middle_name":         row[5] or "",
        "last_name":           row[6] or "",
        "phone_number":        row[7] or "",
        "is_active":           row[8],
        "user_role_id":        row[9] or 2,
        "access_failed_count": row[10] or 0,
    }


def _get_role_name(db: Session, role_id: int) -> str:
    row = db.execute(
        text('SELECT "RoleName" FROM twam."UserRole" WHERE "UserRoleId" = :rid LIMIT 1'),
        {"rid": role_id},
    ).fetchone()
    return row[0] if row else ""


def _increment_access_failed(db: Session, user_id: str, current_count: int):
    new_count = current_count + 1
    is_active = new_count < 3
    db.execute(
        text(f"""
            UPDATE {IDENTITY_USER_TABLE}
            SET "AccessFailedCount" = :cnt, "IsActive" = :active
            WHERE "Id" = :uid
        """),
        {"cnt": new_count, "active": is_active, "uid": user_id},
    )
    db.commit()


def _reset_access_failed(db: Session, user_id: str):
    db.execute(
        text(f'UPDATE {IDENTITY_USER_TABLE} SET "AccessFailedCount" = 0 WHERE "Id" = :uid'),
        {"uid": user_id},
    )
    db.commit()


class AuthResult:
    def __init__(self, success: bool, error: str = "", user: dict = None):
        self.success = success
        self.error   = error
        self.user    = user


def authenticate_user(db: Session, username: str, encrypted_password: str) -> AuthResult:
    user = _get_identity_user_by_username(db, username)
    if not user:
        return AuthResult(False, "not_allowed")
    if not user["is_active"]:
        return AuthResult(False, "locked_out")

    is_valid = verify_password(encrypted_password, user["password_hash"], is_client_encrypted=True)
    if not is_valid:
        _increment_access_failed(db, user["id"], user["access_failed_count"])
        if user["access_failed_count"] + 1 >= 3:
            return AuthResult(False, "locked_out")
        return AuthResult(False, "invalid_credentials")

    _reset_access_failed(db, user["id"])
    return AuthResult(True, user=user)


def build_token_claims(db: Session, user: dict) -> dict:
    role_id   = user["user_role_id"]
    role_name = _get_role_name(db, role_id)
    session   = str(uuid.uuid4())

    first  = user["first_name"]
    middle = user["middle_name"]
    last   = user["last_name"]
    full   = (f"{first} {middle} {last}" if middle else f"{first} {last}").strip()

    return {
        "sub":                user["id"],
        "preferred_username": user["user_name"],
        "name":               full,
        "sid":                session,
        "email":              user["email"],
        "email_id":           user["email"],
        "UserId":             user["id"],
        "session_id":         session,
        "TenantId":           "1",
        "FirstName":          first,
        "MiddleName":         middle,
        "LastName":           last,
        "RoleId":             str(role_id),
        "RoleName":           role_name,
        "role":               role_name,
        "family_name":        last,
        "given_name":         first,
        "phone_number":       user["phone_number"],
    }


def _next_people_id(db: Session) -> Optional[int]:
    try:
        row = db.execute(text(f"SELECT nextval('{PEOPLE_SEQ}')")).fetchone()
        return int(row[0])
    except Exception as e:
        print(f"[Auth] Sequence error: {e}")
        return None


def create_identity_user(db: Session, request: RegisterUserRequest) -> dict:
    # Duplicate phone check
    if request.PhoneNumber:
        row = db.execute(
            text(f'SELECT "Id" FROM {IDENTITY_USER_TABLE} WHERE "PhoneNumber" = :ph LIMIT 1'),
            {"ph": request.PhoneNumber},
        ).fetchone()
        if row:
            return {"succeeded": False, "errors": [
                {"code": "DuplicatePhoneNumber", "description": "Phone number is already taken."}
            ]}

    # Duplicate email check
    if request.EmailId:
        row = db.execute(
            text(f'SELECT "Id" FROM {IDENTITY_USER_TABLE} WHERE "NormalizedEmail" = :em LIMIT 1'),
            {"em": (request.EmailId or "").upper()},
        ).fetchone()
        if row:
            return {"succeeded": False, "errors": [
                {"code": "DuplicateEmail", "description": "Email is already taken."}
            ]}

    plain_password = request.Password or "Admin@12345"
    # _get_password_cipher() reads from AppSettings cache at runtime
    twam_hash      = generate_sha256_hash_with_salt(plain_password, _get_password_cipher())
    stored_hash    = _aspnet_hash_password(twam_hash)

    user_id  = str(uuid.uuid4())
    role_id  = request.RoleId if request.RoleId else 2
    now      = datetime.now(timezone.utc)

    db.execute(
        text(f"""
            INSERT INTO {IDENTITY_USER_TABLE}
            (
                "Id", "UserName", "NormalizedUserName", "Email", "NormalizedEmail",
                "EmailConfirmed", "PasswordHash", "SecurityStamp", "ConcurrencyStamp",
                "PhoneNumber", "PhoneNumberConfirmed", "TwoFactorEnabled",
                "LockoutEnabled", "AccessFailedCount",
                "FirstName", "MiddleName", "LastName",
                "IsActive", "UserRoleId", "CreatedDate", "CreatedBy",
                "ModifiedDate", "ModifiedBy",
                "TenantId", "OrganizationId",
                "DeletedInd", "IsRandomPassword"
            )
            VALUES
            (
                :id, :uname, :nuname, :email, :nemail,
                true, :pwdhash, :stamp, :conc,
                :phone, false, false,
                true, 0,
                :first, :middle, :last,
                true, :role, :now, :created_by,
                NULL, NULL,
                '1', 1,
                false, false
            )
        """),
        {
            "id":         user_id,
            "uname":      request.EmailId,
            "nuname":     (request.EmailId or "").upper(),
            "email":      request.EmailId,
            "nemail":     (request.EmailId or "").upper(),
            "pwdhash":    stored_hash,
            "stamp":      str(uuid.uuid4()),
            "conc":       str(uuid.uuid4()),
            "phone":      request.PhoneNumber or "",
            "first":      request.FirstName or "",
            "middle":     request.MiddleName or "",
            "last":       request.LastName or "",
            "role":       role_id,
            "now":        now,
            "created_by": request.EmailId,
        },
    )

    # Insert into twam.People
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
                "pid":    people_id,
                "first":  request.FirstName or "",
                "middle": request.MiddleName or "",
                "last":   request.LastName or "",
                "uid":    user_id,
                "role":   role_id,
                "email":  request.EmailId or "",
                "phone":  request.PhoneNumber or "",
                "now":    now,
            },
        )

    db.commit()
    return {"succeeded": True, "errors": [], "user_id": user_id}


def reset_password_with_token(db: Session, email: str, new_password: str) -> dict:
    """
    Called after the reset token has been validated in the route.
    Sets the new password directly — no current password required.
    new_password is AES-encrypted by Angular (same as login flow).
    """
    user = _get_identity_user_by_username(db, email)
    if not user:
        return {"succeeded": False, "errors": [{"code": "NotFound", "description": "User not found."}]}

    try:
        new_plain = _decrypt_client_password(new_password)
    except Exception:
        # If decryption fails treat as plain text (direct API call / testing)
        new_plain = new_password

    # _get_password_cipher() reads from AppSettings cache at runtime
    new_twam    = generate_sha256_hash_with_salt(new_plain, _get_password_cipher())
    new_db_hash = _aspnet_hash_password(new_twam)

    db.execute(
        text(f"""
            UPDATE {IDENTITY_USER_TABLE}
            SET "PasswordHash"      = :ph,
                "SecurityStamp"     = :ss,
                "ModifiedDate"      = :now,
                "ModifiedBy"        = :mb,
                "AccessFailedCount" = 0,
                "IsActive"          = true
            WHERE "Id" = :uid
        """),
        {
            "ph":  new_db_hash,
            "ss":  str(uuid.uuid4()),
            "now": datetime.now(timezone.utc),
            "mb":  email,
            "uid": user["id"],
        },
    )
    db.commit()
    return {"succeeded": True, "errors": []}


def change_password(db: Session, email_id: str, current_password: str, new_password: str) -> dict:
    user = _get_identity_user_by_username(db, email_id)
    if not user:
        return {"succeeded": False, "errors": [{"code": "NotFound", "description": "User not found."}]}

    if not verify_password(current_password, user["password_hash"], is_client_encrypted=True):
        return {"succeeded": False, "errors": [{"code": "PasswordMismatch", "description": "Current password is incorrect."}]}

    new_plain   = _decrypt_client_password(new_password)
    # _get_password_cipher() reads from AppSettings cache at runtime
    new_twam    = generate_sha256_hash_with_salt(new_plain, _get_password_cipher())
    new_db_hash = _aspnet_hash_password(new_twam)

    db.execute(
        text(f"""
            UPDATE {IDENTITY_USER_TABLE}
            SET "PasswordHash"  = :ph,
                "SecurityStamp" = :ss,
                "ModifiedDate"  = :now,
                "ModifiedBy"    = :mb
            WHERE "Id" = :uid
        """),
        {"ph": new_db_hash, "ss": str(uuid.uuid4()),
         "now": datetime.now(timezone.utc), "mb": email_id,
         "uid": user["id"]},
    )
    db.commit()
    return {"succeeded": True, "errors": []}