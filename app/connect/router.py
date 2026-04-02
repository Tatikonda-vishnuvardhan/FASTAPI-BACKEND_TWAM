"""
OAuth2 / OIDC compatibility layer for angular-oauth2-oidc.

Angular calls these endpoints (all derived from environment.ts):
  POST /connect/token                         ← login
  GET  /connect/userinfo                      ← get user claims after login
  GET  /.well-known/openid-configuration      ← OIDC discovery (auto)
  POST /api/register/signup                   ← AuthenticationService.createUser()
  POST /api/register/ChangePassword           ← PasswordManagementService.changePassword()
  POST /api/register/SendResetPasswordLink    ← legacy link-based reset
  POST /api/register/SendForgotPasswordOtp    ← NEW: OTP-based forgot password (step 1)
  POST /api/register/VerifyForgotPasswordOtp  ← NEW: OTP-based forgot password (step 2)
  POST /api/register/ResetPassword            ← set new password after OTP verify (step 3)
  POST /api/register/update                   ← PasswordManagementService.update()
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
import jwt

from database import get_db
from app.auth.repository import (
    authenticate_user, build_token_claims,
    create_identity_user, change_password,
    _get_identity_user_by_username, IDENTITY_USER_TABLE,
    reset_password_with_token,
)
from app.auth.security import create_access_token, EXPIRES_MINUTES, decode_token, decode_reset_token
from app.auth.schemas import (
    RegisterUserRequest, TokenResponse, ChangePasswordRequest,
    ResetPasswordRequest, ResetPasswordConfirmRequest,
    OtpRequest, OtpVerifyRequest,
)
from app.auth.dependencies import _bearer_scheme, get_current_user, CurrentUser
from app.sendemail.repository import send_email
from app.sendemail.schemas import EmailCreate

router = APIRouter(tags=["OAuth2 Compatibility"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

# ── In-memory OTP store: { email_lower: { otp, expires_at, attempts } }
# For production with multiple workers use Redis instead.
_otp_store: dict[str, dict] = {}

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _otp_email_html(full_name: str, otp: str) -> str:
    """Return a branded HTML email body for the OTP."""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background:#f5f6fa;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f6fa;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#6A012A,#a0023f);
                     padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;
                       letter-spacing:2px;">ONLY TWAM</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.75);font-size:13px;">
              Password Reset Request
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 40px 32px;">
            <p style="margin:0 0 16px;font-size:15px;color:#333;">
              Hi <strong>{full_name}</strong>,
            </p>
            <p style="margin:0 0 24px;font-size:14px;color:#555;line-height:1.6;">
              We received a request to reset your password. Use the verification
              code below to continue. This code is valid for
              <strong>{OTP_TTL_MINUTES} minutes</strong>.
            </p>

            <!-- OTP Box -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding:8px 0 28px;">
                  <div style="display:inline-block;background:#fdf3f6;
                               border:2px dashed #d4789a;border-radius:12px;
                               padding:20px 40px;">
                    <p style="margin:0 0 6px;font-size:11px;color:#888;
                               letter-spacing:2px;text-transform:uppercase;">
                      Your OTP Code
                    </p>
                    <p style="margin:0;font-size:40px;font-weight:800;
                               letter-spacing:12px;color:#6A012A;">
                      {otp}
                    </p>
                  </div>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 24px;font-size:13px;color:#888;line-height:1.6;">
              Enter this code on the verification page. Do not share this code
              with anyone. If you did not request a password reset, please
              ignore this email — your account is safe.
            </p>

            <!-- Divider -->
            <hr style="border:none;border-top:1px solid #f0e0e6;margin:0 0 24px;"/>

            <p style="margin:0;font-size:12px;color:#bbb;text-align:center;">
              &copy; {datetime.now().year} Only TWAM. All rights reserved.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _otp_email_plain(full_name: str, otp: str) -> str:
    return (
        f"Hello {full_name},\n\n"
        f"We received a request to reset your Only TWAM password.\n\n"
        f"Your one-time verification code is:\n\n"
        f"  {otp}\n\n"
        f"This code expires in {OTP_TTL_MINUTES} minutes.\n"
        f"Do not share it with anyone.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Regards,\nTWAM Team"
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /connect/token
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/connect/token", response_model=TokenResponse)
async def connect_token(
    grant_type:    str           = Form(...),
    username:      str           = Form(...),
    password:      str           = Form(...),
    client_id:     str           = Form(default="twam-web-portal"),
    client_secret: str           = Form(default="twamsecret"),
    scope:         Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    if grant_type != "password":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    if client_id != "twam-web-portal" or client_secret != "twamsecret":
        raise HTTPException(status_code=401, detail="invalid_client")

    result = authenticate_user(db, username, password)
    if not result.success:
        error_map = {
            "not_allowed":         "not allowed",
            "locked_out":          "locked out",
            "invalid_credentials": "invalid credentials",
        }
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_grant",
                    "error_description": error_map.get(result.error, "Authentication failed.")}
        )

    claims = build_token_claims(db, result.user)
    return TokenResponse(
        access_token=create_access_token(claims),
        expires_in=EXPIRES_MINUTES * 60
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /connect/userinfo
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/connect/userinfo")
async def connect_userinfo(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─────────────────────────────────────────────────────────────────────────────
# GET /.well-known/openid-configuration
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/.well-known/openid-configuration")
async def oidc_discovery(request: Request):
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "issuer":                                base,
        "authorization_endpoint":                f"{base}/connect/authorize",
        "token_endpoint":                        f"{base}/connect/token",
        "userinfo_endpoint":                     f"{base}/connect/userinfo",
        "end_session_endpoint":                  f"{base}/connect/endsession",
        "revocation_endpoint":                   f"{base}/connect/revocation",
        "jwks_uri":                              f"{base}/.well-known/jwks",
        "response_types_supported":              ["code", "token"],
        "grant_types_supported":                 ["password", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "subject_types_supported":               ["public"],
        "id_token_signing_alg_values_supported": ["HS512"],
    })


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/signup
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/signup", status_code=201)
async def register_signup(request: RegisterUserRequest, db: Session = Depends(get_db)):
    result = create_identity_user(db, request)
    if result["succeeded"]:
        return {"message": "User created successfully.", "userId": result["user_id"]}
    raise HTTPException(status_code=400, detail={"errors": result["errors"]})


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/ChangePassword
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/ChangePassword")
async def register_change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    result = change_password(db, request.EmailId, request.CurrentPassword, request.NewPassword)
    if result["succeeded"]:
        return {"message": "Password has been changed successfully."}
    raise HTTPException(status_code=400, detail={"errors": result["errors"]})


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/SendResetPasswordLink  (legacy link-based flow — kept)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/SendResetPasswordLink")
async def register_reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    generic_response = {"message": "Reset Password has been sent to mail."}

    user = _get_identity_user_by_username(db, request.EmailId)
    print(f"DEBUG: Looking up '{request.EmailId}' → found: {user is not None}")
    if not user:
        return generic_response

    reset_token = create_access_token(
        user_claims={"sub": user["email"], "purpose": "password_reset", "email": user["email"]},
        expires_minutes=15,
    )
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    print(f"DEBUG: Reset link generated: {reset_link}")

    full_name = f"{user['first_name']} {user['last_name']}".strip() or user["email"]
    sent = send_email(db, EmailCreate(
        name    = full_name,
        email   = user["email"],
        subject = "Reset Your Password — Only TWAM",
        message = (
            f"Hello {full_name},\n\n"
            f"Click the link below to reset your password (valid for 15 minutes):\n"
            f"{reset_link}\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Regards,\nTWAM Team"
        ),
        filename=None, isFile=False, data=None,
    ))
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send reset email. Please try again later.")

    return generic_response


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/SendForgotPasswordOtp  ← NEW
# Step 1: Generate a 6-digit OTP, store it in memory, and email it.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/SendForgotPasswordOtp")
async def send_forgot_password_otp(request: OtpRequest, db: Session = Depends(get_db)):
    """
    Looks up the user by email, generates a 6-digit OTP valid for 10 minutes,
    stores it in the in-memory OTP store, and sends it via email.
    Always returns the same generic message to prevent email enumeration.
    """
    generic_response = {"message": "If this email is registered, an OTP has been sent."}

    # Normalise key
    email_key = request.EmailId.strip().lower()

    # Look up user — if not found return generic (no enumeration)
    user = _get_identity_user_by_username(db, request.EmailId.strip())
    if not user:
        print(f"DEBUG OTP: User not found for '{request.EmailId}'")
        return generic_response

    # Generate OTP and store with expiry
    otp = _generate_otp(6)
    _otp_store[email_key] = {
        "otp":        otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
        "attempts":   0,
    }
    print(f"DEBUG OTP: Generated OTP {otp} for {email_key} (expires in {OTP_TTL_MINUTES} min)")

    # Build email
    full_name = f"{user['first_name']} {user['last_name']}".strip() or user["email"]
    html_body = _otp_email_html(full_name, otp)
    plain_body = _otp_email_plain(full_name, otp)

    # Try HTML email first; send_email sends plain text, so we embed HTML as message
    sent = send_email(db, EmailCreate(
        name    = full_name,
        email   = user["email"],
        subject = f"Your TWAM Password Reset OTP — {otp}",   # OTP in subject as fallback
        message = html_body,   # send_email wraps this in MIMEText("plain") — see note below
        filename=None, isFile=False, data=None,
    ))

    if not sent:
        # Remove OTP from store so user can retry immediately
        _otp_store.pop(email_key, None)
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please try again later."
        )

    return generic_response


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/VerifyForgotPasswordOtp  ← NEW
# Step 2: Validate OTP → return a short-lived JWT reset token.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/VerifyForgotPasswordOtp")
async def verify_forgot_password_otp(request: OtpVerifyRequest, db: Session = Depends(get_db)):
    """
    Validates the OTP submitted by the user.
    On success: clears the OTP from store, returns a 15-minute password-reset JWT.
    On failure: increments attempt counter; locks out after OTP_MAX_ATTEMPTS bad attempts.
    """
    email_key = request.EmailId.strip().lower()

    # 1. Look up OTP record
    record = _otp_store.get(email_key)
    if not record:
        raise HTTPException(
            status_code=400,
            detail="No OTP was requested for this email, or it has already been used."
        )

    # 2. Check expiry
    if datetime.now(timezone.utc) > record["expires_at"]:
        _otp_store.pop(email_key, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # 3. Check max attempts
    if record["attempts"] >= OTP_MAX_ATTEMPTS:
        _otp_store.pop(email_key, None)
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. Please request a new OTP."
        )

    # 4. Verify OTP value
    submitted = request.Otp.strip()
    if submitted != record["otp"]:
        record["attempts"] += 1
        remaining = OTP_MAX_ATTEMPTS - record["attempts"]
        print(f"DEBUG OTP: Wrong OTP for {email_key}. Attempt {record['attempts']}/{OTP_MAX_ATTEMPTS}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )

    # 5. OTP is correct — consume it immediately (single-use)
    _otp_store.pop(email_key, None)
    print(f"DEBUG OTP: OTP verified for {email_key}")

    # 6. Verify user still exists in DB
    user = _get_identity_user_by_username(db, request.EmailId.strip())
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 7. Issue a short-lived password-reset JWT (15 minutes)
    reset_token = create_access_token(
        user_claims={
            "sub":     user["email"],
            "email":   user["email"],
            "purpose": "password_reset",
        },
        expires_minutes=15,
    )

    return {
        "message": "OTP verified successfully.",
        "token":   reset_token,
        "email":   user["email"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/ResetPassword
# Step 3: Validate the JWT reset token and set the new password.
# Accepts both the legacy (token-link) and new OTP flow.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/ResetPassword")
async def register_confirm_reset(
    request: ResetPasswordConfirmRequest,
    db: Session = Depends(get_db),
):
    # 1. Decode + validate the reset JWT
    try:
        payload = decode_reset_token(request.Token)
    except Exception as e:
        print(f"DEBUG: Token decode failed — {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    # 2. Ensure it's a password-reset token, not a regular login token
    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    # 3. Resolve email — prefer token's own email claim for security
    email = payload.get("email") or payload.get("sub") or (request.EmailId or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Cannot determine user email from token.")

    # 4. Reset the password
    result = reset_password_with_token(db, email, request.NewPassword)
    if not result["succeeded"]:
        raise HTTPException(status_code=400, detail={"errors": result["errors"]})

    return {"message": "Password has been reset successfully. You can now log in."}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register/update
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/register/update")
async def register_update(
    request: RegisterUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not request.EmailId:
        raise HTTPException(status_code=400, detail="EmailId is required.")

    user = _get_identity_user_by_username(db, request.EmailId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    no_change = (
        (request.FirstName   or "") == (user["first_name"]   or "") and
        (request.MiddleName  or "") == (user["middle_name"]  or "") and
        (request.LastName    or "") == (user["last_name"]    or "") and
        (request.PhoneNumber or "") == (user["phone_number"] or "")
    )
    if no_change:
        raise HTTPException(status_code=400, detail="No changes detected. Profile is already up to date.")

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
            SET "FirstName"=:first,"MiddleName"=:middle,"LastName"=:last,
                "PhoneNumber"=:phone,"ModifiedDate"=NOW()
            WHERE "UserProfileId"=:uid
        """),
        {"first": request.FirstName or "", "middle": request.MiddleName or "",
         "last": request.LastName or "", "phone": request.PhoneNumber or "",
         "uid": user["id"]},
    )
    db.commit()
    return {"message": "User updated successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# Stubs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/connect/authorize")
async def connect_authorize():
    return {"message": "Use password flow via /connect/token"}

@router.post("/connect/revocation")
async def connect_revocation():
    return {"message": "Token revoked"}

@router.get("/connect/endsession")
async def connect_endsession():
    return {"message": "Session ended"}
