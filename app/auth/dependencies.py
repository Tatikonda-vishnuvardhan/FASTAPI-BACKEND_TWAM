"""
app/auth/dependencies.py — Fixed
Fixes:
  1. RoleId is stored as string in JWT ("2") but int expected — safe conversion
  2. 401 response code added (frontend handles 401 redirect); 403 for role failures
  3. get_current_user returns 401 (not 403) for missing/expired tokens
     so the frontend axios interceptor can auto-redirect to login
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import jwt

from .security import decode_token
from .schemas import CurrentUser

# ── Role constants ─────────────────────────────────────────────────────────────

class Roles:
    SUPER_ADMIN       = 1
    USER              = 2
    INVENTORY_MANAGER = 3
    PRODUCT_MANAGER   = 4
    ORDER_MANAGER     = 5
    CUSTOMER_SUPPORT  = 6

    NAMES = {
        1: "Super Admin",
        2: "User",
        3: "Inventory Manager",
        4: "Product Manager",
        5: "Order Manager",
        6: "Customer Support",
    }

    STAFF = {1, 3, 4, 5, 6}
    ALL   = {1, 2, 3, 4, 5, 6}


# ── Bearer extractor ───────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


# ── get_current_user ───────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    Returns HTTP 401 for missing/expired tokens (triggers frontend redirect).
    Returns HTTP 403 for invalid tokens or missing claims.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid authentication token: {str(e)[:100]}",
        )

    email_id = payload.get("email_id") or payload.get("email")
    if not email_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing required claim: email_id",
        )

    # RoleId is stored as string in JWT ("2") — safely convert
    role_id_raw = payload.get("RoleId") or payload.get("roleId") or 0
    try:
        role_id = int(role_id_raw)
    except (TypeError, ValueError):
        role_id = 0

    # user_id comes from "sub" claim = UserProfileId (GUID)
    user_id = str(payload.get("sub") or payload.get("UserId") or "")

    return CurrentUser(
        user_id    = user_id,
        email      = email_id,
        role_id    = role_id,
        role_name  = payload.get("RoleName") or payload.get("role") or "",
        first_name = payload.get("FirstName") or payload.get("given_name") or "",
        last_name  = payload.get("LastName")  or payload.get("family_name") or "",
        full_name  = payload.get("name") or "",
        tenant_id  = str(payload.get("TenantId") or "1"),
    )


# ── Optional user ──────────────────────────────────────────────────────────────

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[CurrentUser]:
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ── Role-gated factory ─────────────────────────────────────────────────────────

def require_roles(*allowed_role_ids: int):
    allowed = set(allowed_role_ids)

    async def _check(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role_id not in allowed:
            role_names = [Roles.NAMES.get(r, str(r)) for r in sorted(allowed)]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(role_names)}.",
            )
        return current_user

    return _check


# ── Admin user dependency ──────────────────────────────────────────────────────

async def get_current_admin_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Requires Super Admin or Order Manager."""
    allowed = {Roles.SUPER_ADMIN, Roles.ORDER_MANAGER}
    if current_user.role_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Order Manager role required.",
        )
    return current_user


# ── Shortcuts ──────────────────────────────────────────────────────────────────

def require_super_admin():
    return require_roles(Roles.SUPER_ADMIN)

def require_staff():
    return require_roles(*Roles.STAFF)

def require_admin_or_order_manager():
    return require_roles(Roles.SUPER_ADMIN, Roles.ORDER_MANAGER)

def require_inventory_access():
    return require_roles(Roles.SUPER_ADMIN, Roles.INVENTORY_MANAGER, Roles.PRODUCT_MANAGER)
