"""
Auth routes — mirrors:
  IdentityServer4 /connect/token  → POST /auth/token
  RegisterController              → POST /auth/signup, /auth/update, etc.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from sqlalchemy import text

from database import get_db
from .schemas import (
    TokenResponse, RegisterUserRequest,
    ChangePasswordRequest, ResetPasswordRequest, ResetPasswordConfirmRequest,
)
from .repository import (
    authenticate_user, build_token_claims,
    create_identity_user, change_password,
    _get_identity_user_by_username, IDENTITY_USER_TABLE,
    reset_password_with_token,
)
from .security import create_access_token, decode_token, decode_reset_token, EXPIRES_MINUTES
from .dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ── Read frontend URL from env (used in reset-password links) ─────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN — POST /auth/token
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/token", response_model=TokenResponse, summary="Login — get JWT access token")
async def token(
    grant_type:    str           = Form(...),
    username:      str           = Form(...),
    password:      str           = Form(...),
    client_id:     str           = Form(default="twam-web-portal"),
    client_secret: str           = Form(default="twamsecret"),
    scope:         Optional[str] = Form(default=None),
    db:            Session       = Depends(get_db),
):
    if grant_type != "password":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    if client_id != "twam-web-portal" or client_secret != "twamsecret":
        raise HTTPException(status_code=401, detail="invalid_client")

    result = authenticate_user(db, username, password)

    if not result.success:
        error_map = {
            "not_allowed":         "User not found.",
            "locked_out":          "Account is locked. Please reset your password.",
            "invalid_credentials": "Invalid username or password.",
        }
        raise HTTPException(status_code=400, detail=error_map.get(result.error, "Authentication failed."))

    claims       = build_token_claims(db, result.user)
    access_token = create_access_token(claims)

    return TokenResponse(access_token=access_token, expires_in=EXPIRES_MINUTES * 60)


# ─────────────────────────────────────────────────────────────────────────────
# SIGNUP — POST /auth/signup
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=201, summary="Register a new user")
async def signup(request: RegisterUserRequest, db: Session = Depends(get_db)):
    result = create_identity_user(db, request)
    if result["succeeded"]:
        return {"message": "User created successfully.", "userId": result["user_id"]}
    raise HTTPException(status_code=400, detail={"errors": result["errors"]})


@router.post("/guest-signup", status_code=201, summary="Register a guest/user-role account")
async def guest_signup(request: RegisterUserRequest, db: Session = Depends(get_db)):
    request.RoleId = request.RoleId or Roles.USER
    result = create_identity_user(db, request)
    if result["succeeded"]:
        return {"Succeeded": True, "message": "User created successfully.", "userId": result["user_id"]}
    raise HTTPException(status_code=400, detail={"message": "User creation failed.", "errors": result["errors"]})


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE PROFILE — POST /auth/update
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/update", summary="Update current user profile (requires login)")
async def update_profile(
    request:      RegisterUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db:           Session     = Depends(get_db),
):
    if not request.EmailId:
        raise HTTPException(status_code=400, detail="EmailId is required.")

    user = _get_identity_user_by_username(db, request.EmailId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db.execute(
        text(f"""
            UPDATE {IDENTITY_USER_TABLE}
            SET "FirstName"   = :first,
                "MiddleName"  = :middle,
                "LastName"    = :last,
                "PhoneNumber" = :phone
            WHERE "Id" = :uid
        """),
        {"first": request.FirstName or "", "middle": request.MiddleName or "",
         "last": request.LastName or "", "phone": request.PhoneNumber or "",
         "uid": user["id"]},
    )
    db.execute(
        text("""
            UPDATE twam."People"
            SET "FirstName"   = :first,
                "MiddleName"  = :middle,
                "LastName"    = :last,
                "PhoneNumber" = :phone,
                "ModifiedDate" = NOW()
            WHERE "UserProfileId" = :uid
        """),
        {"first": request.FirstName or "", "middle": request.MiddleName or "",
         "last": request.LastName or "", "phone": request.PhoneNumber or "",
         "uid": user["id"]},
    )
    db.commit()
    return {"message": "User updated successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE USER (admin) — POST /auth/updateUser
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/updateUser", summary="Admin: update user role / active status")
async def update_user(
    request:      RegisterUserRequest,
    current_user: CurrentUser = Depends(require_roles(Roles.SUPER_ADMIN)),
    db:           Session     = Depends(get_db),
):
    if not request.EmailId:
        raise HTTPException(status_code=400, detail="EmailId is required.")

    user = _get_identity_user_by_username(db, request.EmailId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db.execute(
        text(f"""
            UPDATE {IDENTITY_USER_TABLE}
            SET "IsActive"          = :active,
                "UserRoleId"        = :role,
                "AccessFailedCount" = 0,
                "LockoutEnd"        = NULL
            WHERE "Id" = :uid
        """),
        {"active": request.IsActive, "role": request.RoleId, "uid": user["id"]},
    )
    db.execute(
        text("""
            UPDATE twam."People"
            SET "IsActive" = :active, "RoleId" = :role, "ModifiedDate" = NOW()
            WHERE "UserProfileId" = :uid
        """),
        {"active": request.IsActive, "role": request.RoleId, "uid": user["id"]},
    )
    db.commit()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ChangePassword", summary="Change password (requires login)")
async def change_password_endpoint(
    request:      ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db:           Session     = Depends(get_db),
):
    if not request.EmailId:
        raise HTTPException(status_code=400, detail="EmailId is required.")

    result = change_password(db, request.EmailId, request.CurrentPassword, request.NewPassword)
    if result["succeeded"]:
        return {"message": "Password has been changed successfully."}
    raise HTTPException(status_code=400, detail={"errors": result["errors"]})


# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — POST /auth/SendResetPasswordLink
# Looks up the user, generates a 15-min JWT reset token, and emails the link.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/SendResetPasswordLink", summary="Send password reset email")
async def send_reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Always return the same message to avoid user enumeration
    generic_response = {"message": "If this email is registered, a reset link has been sent."}

    # 1. Look up user
    user = _get_identity_user_by_username(db, request.EmailId)
    print(f"DEBUG: Looking up '{request.EmailId}' → found: {user is not None}")  # ← add here
    if not user:
        return generic_response

    # 2. Generate a short-lived reset token (15 minutes)
    reset_token = create_access_token(
        user_claims={
            "sub":     user["email"],
            "purpose": "password_reset",
            "email":   user["email"],
        },
        expires_minutes=15,
    )

    # 3. Build the reset link
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    # 4. Send the email via email.repository
    try:
        from app.email.repository import send_email
        from app.email.schemas import EmailCreate

        full_name = f"{user['first_name']} {user['last_name']}".strip() or user["email"]

        email_payload = EmailCreate(
            name     = full_name,
            email    = user["email"],
            subject  = request.Subject or "Reset Your Password",
            message  = (
                f"Hello {full_name},\n\n"
                f"We received a request to reset your password.\n\n"
                f"Click the link below to reset it (valid for 15 minutes):\n"
                f"{reset_link}\n\n"
                f"If you did not request this, please ignore this email.\n\n"
                f"Regards,\nTWAM Team"
            ),
            filename = None,
            isFile   = False,
            data     = None,
        )

        sent = send_email(db, email_payload)
        if not sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send reset email. Please try again later."
            )

    except ImportError:
        raise HTTPException(status_code=500, detail="Email service not available.")

    return generic_response


# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD — POST /auth/ResetPassword
# Validates the token from the email link and sets the new password.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ResetPassword", summary="Reset password using token from email link")
async def reset_password(request: ResetPasswordConfirmRequest, db: Session = Depends(get_db)):
    # 1. Decode and validate the reset token
    try:
        payload = decode_reset_token(request.Token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    # 2. Verify token was issued for password reset (not a regular login token)
    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    email = payload.get("email") or payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    # 3. Reset the password
    result = reset_password_with_token(db, email, request.NewPassword)
    if not result["succeeded"]:
        raise HTTPException(status_code=400, detail={"errors": result["errors"]})

    return {"message": "Password has been reset successfully. You can now log in."}


# ─────────────────────────────────────────────────────────────────────────────
# ME — GET /auth/me
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=CurrentUser, summary="Get current user info from token")
async def me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user

# ─────────────────────────────────────────────────────────────────────────────
# OTP — for guest checkout account creation + password reset
# ─────────────────────────────────────────────────────────────────────────────

import random
import string
from datetime import datetime, timedelta, timezone

_OTP_TTL_MINUTES = 10
_OTP_TABLE = 'auth."OtpStore"'


def _ensure_otp_table(db: Session) -> None:
    """Create auth.OtpStore table if it doesn't exist."""
    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {_OTP_TABLE} (
            "Email"     VARCHAR(255) PRIMARY KEY,
            "Otp"       VARCHAR(10)  NOT NULL,
            "ExpiresAt" TIMESTAMPTZ  NOT NULL,
            "Purpose"   VARCHAR(50)  DEFAULT 'guest_checkout'
        )
    """))
    db.commit()


def _generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))


def _otp_store(db: Session, email: str, otp: str, purpose: str) -> None:
    expires = datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES)
    db.execute(text(f"""
        INSERT INTO {_OTP_TABLE} ("Email", "Otp", "ExpiresAt", "Purpose")
        VALUES (:email, :otp, :expires, :purpose)
        ON CONFLICT ("Email") DO UPDATE
            SET "Otp" = EXCLUDED."Otp",
                "ExpiresAt" = EXCLUDED."ExpiresAt",
                "Purpose" = EXCLUDED."Purpose"
    """), {"email": email, "otp": otp, "expires": expires, "purpose": purpose})
    db.commit()


def _otp_get(db: Session, email: str) -> dict | None:
    row = db.execute(text(f"""
        SELECT "Otp", "ExpiresAt", "Purpose"
        FROM {_OTP_TABLE}
        WHERE "Email" = :email
    """), {"email": email}).fetchone()
    if not row:
        return None
    return {"otp": row[0], "expires_at": row[1], "purpose": row[2]}


def _otp_delete(db: Session, email: str) -> None:
    db.execute(text(f'DELETE FROM {_OTP_TABLE} WHERE "Email" = :email'), {"email": email})
    db.commit()


@router.post("/send-otp", summary="Send OTP to email for guest checkout or verification")
async def send_otp(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Send a 6-digit OTP to the provided email.
    Used by guest checkout to verify email before creating an account.

    Body: { "email": "user@example.com", "purpose": "guest_checkout" | "reset_password" }
    """
    email   = (payload.get("email") or "").strip().lower()
    purpose = payload.get("purpose", "guest_checkout")

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required.")

    # Check if email already registered - tell user to login instead
    if purpose == "guest_checkout":
        existing = _get_identity_user_by_username(db, email)
        if existing:
            raise HTTPException(
                status_code=409,
                detail={"message": "This email is already registered. Please sign in to continue.", "exists": True}
            )

    otp = _generate_otp()
    _ensure_otp_table(db)
    _otp_store(db, email, otp, purpose)

    # Send via email service
    try:
        from app.sendemail.repository import send_email
        from app.sendemail.schemas import EmailCreate

        subject = "Your TWAM Verification Code"
        body = f"""
        <div style="font-family: 'Trebuchet MS', Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px 24px; background: #fff; border-radius: 12px; border: 1px solid #e8d8de;">
          <img src="https://twam.in/assets/Twam-Logo-Black.png" alt="TWAM" style="height: 40px; margin-bottom: 24px; display: block;" />
          <h2 style="color: #6B0F2A; margin: 0 0 8px; font-size: 22px;">Your Verification Code</h2>
          <p style="color: #555; margin: 0 0 24px; font-size: 14px;">Use this OTP to complete your checkout. It expires in {_OTP_TTL_MINUTES} minutes.</p>
          <div style="background: #f5f0e6; border: 2px dashed #6B0F2A; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px; font-weight: 800; color: #6B0F2A; letter-spacing: 8px;">{otp}</span>
          </div>
          <p style="color: #aaa; font-size: 12px; margin: 0;">If you didn't request this, please ignore this email.</p>
        </div>
        """

        send_email(db, EmailCreate(
            email=email,
            subject=subject,
            message=body,
        ))
        print(f"✅ OTP sent to {email}: {otp}")
    except Exception as e:
        # Log but don't fail — OTP is in memory, can still verify
        print(f"⚠️  Email send failed for {email}: {e}")
        print(f"   OTP for {email}: {otp}")  # visible in server logs for dev

    return {"success": True, "message": f"OTP sent to {email}. Valid for {_OTP_TTL_MINUTES} minutes."}


@router.post("/verify-otp", summary="Verify OTP and create guest account if purpose=guest_checkout")
async def verify_otp(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Verify the OTP.
    If purpose=guest_checkout, creates a user account with OTP as temporary password
    and returns a login token so the guest can proceed as authenticated user.

    Body: {
      "email": "user@example.com",
      "otp": "123456",
      "purpose": "guest_checkout",
      "firstName": "...",   // optional - for account creation
      "phone": "..."        // optional
    }
    """
    email   = (payload.get("email") or "").strip().lower()
    otp     = (payload.get("otp") or "").strip()
    purpose = payload.get("purpose", "guest_checkout")

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP are required.")

    _ensure_otp_table(db)
    stored = _otp_get(db, email)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

    print(f"🔍 OTP verify — stored: '{stored['otp']}' received: '{otp}' match: {stored['otp'] == otp}")
    if stored["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and try again.")

    expires_at = stored["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        _otp_delete(db, email)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # OTP is valid — but DON'T delete yet; delete only after the operation succeeds

    if purpose == "guest_checkout":
        # Create or get user account
        existing = _get_identity_user_by_username(db, email)

        DEFAULT_PASSWORD = "twam@1234"

        if not existing:
            # Create new account with default password twam@1234
            from app.auth.schemas import RegisterUserRequest as RUR
            first_name = payload.get("firstName") or email.split("@")[0]
            reg = RUR(
                FirstName   = first_name,
                LastName    = payload.get("lastName") or "",
                EmailId     = email,
                Password    = DEFAULT_PASSWORD,
                PhoneNumber = payload.get("phone") or "",
                IsActive    = True,
                RoleId      = Roles.USER,
            )
            result = create_identity_user(db, reg)
            if not result["succeeded"]:
                # Don't delete OTP — let user retry
                raise HTTPException(status_code=500, detail="Account creation failed. Please try again.")
            print(f"✅ Guest account created for {email}")

            # Send welcome email with login credentials
            try:
                from app.sendemail.repository import send_email
                from app.sendemail.schemas import EmailCreate
                welcome_body = f"""
                <div style="font-family: 'Trebuchet MS', Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px 24px; background: #fff; border-radius: 12px; border: 1px solid #e8d8de;">
                  <img src="https://twam.in/assets/Twam-Logo-Black.png" alt="TWAM" style="height: 40px; margin-bottom: 24px; display: block;" />
                  <h2 style="color: #6B0F2A; margin: 0 0 8px; font-size: 22px;">Welcome to TWAM!</h2>
                  <p style="color: #555; margin: 0 0 16px; font-size: 14px;">
                    Hi {first_name}, your TWAM account has been created. You can now log in and track your orders.
                  </p>
                  <div style="background: #f5f0e6; border: 1px solid #e8d8de; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px;">
                    <p style="margin: 0 0 6px; font-size: 13px; color: #888;">Your login credentials:</p>
                    <p style="margin: 0 0 4px; font-size: 14px;"><strong>Email:</strong> {email}</p>
                    <p style="margin: 0; font-size: 14px;"><strong>Password:</strong> twam@1234</p>
                  </div>
                  <p style="color: #e53935; font-size: 13px; margin: 0 0 20px;">
                    ⚠️ Please change your password after your first login for security.
                  </p>
                  <a href="https://onlytwam.com/login" style="display: inline-block; background: #6B0F2A; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600;">
                    Login to TWAM
                  </a>
                  <p style="color: #aaa; font-size: 12px; margin: 24px 0 0;">If you didn't create this account, please contact us at customersupport@onlytwam.com</p>
                </div>
                """
                send_email(db, EmailCreate(
                    name=first_name,
                    email=email,
                    subject="Welcome to TWAM — Your Account is Ready",
                    message=welcome_body,
                ))
                print(f"✅ Welcome email sent to {email}")
            except Exception as e:
                print(f"⚠️  Welcome email failed for {email}: {e}")
        else:
            print(f"ℹ️  Existing account found for {email} — logging in")

        # Build login token
        user = _get_identity_user_by_username(db, email)
        if not user:
            raise HTTPException(status_code=500, detail="Could not retrieve user account.")

        claims       = build_token_claims(db, user)
        access_token = create_access_token(claims)

        # NOW delete OTP — everything succeeded
        _otp_delete(db, email)

        return {
            "success":      True,
            "access_token": access_token,
            "token_type":   "Bearer",
            "is_new_user":  not existing,
            "message":      "Account verified successfully.",
        }

    # For password reset purpose — just confirm OTP was valid
    _otp_delete(db, email)
    return {"success": True, "message": "OTP verified. You may now reset your password."}