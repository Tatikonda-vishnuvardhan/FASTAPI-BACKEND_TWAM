from pydantic import BaseModel, Field
from typing import Optional


class TokenRequest(BaseModel):
    grant_type:    str
    username:      str
    password:      str
    # client_id and client_secret are accepted from the request but validated
    # against AppSettings at runtime — defaults removed to avoid leaking values
    # in OpenAPI schema docs.
    client_id:     Optional[str] = None
    client_secret: Optional[str] = None
    scope:         Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "Bearer"
    expires_in:   int = 3600
    scope:        str = "twam-web-portal read write openid profile email"


class RegisterUserRequest(BaseModel):
    FirstName:   Optional[str]  = Field(None, alias="firstName")
    MiddleName:  Optional[str]  = Field(None, alias="middleName")
    LastName:    Optional[str]  = Field(None, alias="lastName")
    EmailId:     Optional[str]  = Field(None, alias="emailId")
    Password:    Optional[str]  = Field(None, alias="password")
    PhoneNumber: Optional[str]  = Field(None, alias="phoneNumber")
    IsActive:    Optional[bool] = Field(True,  alias="isActive")
    RoleId:      int            = Field(2,      alias="roleId")

    model_config = {"populate_by_name": True}


class ChangePasswordRequest(BaseModel):
    EmailId:         str = Field(..., alias="emailId")
    CurrentPassword: str = Field(..., alias="currentPassword")
    NewPassword:     str = Field(..., alias="newPassword")

    model_config = {"populate_by_name": True}


class ResetPasswordRequest(BaseModel):
    """Step 1 — user submits their email to receive a reset link."""
    EmailId: str = Field(..., alias="emailId")
    Subject: str = Field("",  alias="subject")

    model_config = {"populate_by_name": True}


class ResetPasswordConfirmRequest(BaseModel):
    """Step 2 — user submits the token + new password (token-link flow or OTP flow)."""
    EmailId:     Optional[str] = Field(None, alias="emailId")
    Token:       str           = Field(...,  alias="token")
    NewPassword: str           = Field(...,  alias="newPassword")

    model_config = {"populate_by_name": True}


# ── OTP flow ──────────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    """Send a 6-digit OTP to the user's registered email."""
    EmailId: str = Field(..., alias="EmailId")

    model_config = {"populate_by_name": True}


class OtpVerifyRequest(BaseModel):
    """Verify OTP — returns a short-lived reset token on success."""
    EmailId: str = Field(..., alias="EmailId")
    Otp:     str = Field(..., alias="Otp")

    model_config = {"populate_by_name": True}


class CurrentUser(BaseModel):
    user_id:    str
    email:      str
    role_id:    int
    role_name:  str
    first_name: str = ""
    last_name:  str = ""
    full_name:  str = ""
    tenant_id:  str = "1"
