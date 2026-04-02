"""
FastAPI dependency injection for authentication and role-based authorization.

Mirrors:
  AuthorizeFilterAttribute         → get_current_user (requires valid JWT + email_id claim)
  [Authorize(Roles = "Super Admin")] → require_roles(...)
  TWAMConstants.RoleConstants      → role constants
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import jwt

from .security import decode_token
from .schemas import CurrentUser

# ── Constants — mirrors TWAMConstants.RoleConstants ───────────────────────────

class Roles:
    SUPER_ADMIN       = 1
    USER              = 2
    INVENTORY_MANAGER = 3
    PRODUCT_MANAGER   = 4
    ORDER_MANAGER     = 5
    CUSTOMER_SUPPORT  = 6

    # Human-readable names (mirror twam.UserRole.RoleName)
    NAMES = {
        1: "Super Admin",
        2: "User",
        3: "Inventory Manager",
        4: "Product Manager",
        5: "Order Manager",
        6: "Customer Support",
    }

    # All staff roles (everything except end-user)
    STAFF = {1, 3, 4, 5, 6}
    ALL   = {1, 2, 3, 4, 5, 6}


# ── Bearer token extractor ────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Core dependency: get_current_user ─────────────────────────────────────────
# Mirrors AuthorizeFilterAttribute.OnAuthorizationAsync
#   • Requires a valid JWT (authenticated)
#   • Requires the "email_id" claim  (RequireClaim("email_id") in Extensions.cs)
#   • Returns 403 (not 401) matching the .NET behaviour

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    Validates Bearer token and returns the current user's claims.
    Returns HTTP 403 on any failure — matches .NET AuthorizeFilterAttribute (StatusCodeResult(403)).
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required.",
        )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token.",
        )

    # Mirror RequireClaim("email_id")
    email_id = payload.get("email_id")
    if not email_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required claim: email_id.",
        )

    try:
        role_id = int(payload.get("RoleId", 0))
    except (TypeError, ValueError):
        role_id = 0

    return CurrentUser(
        user_id    = payload.get("sub") or payload.get("UserId", ""),
        email      = email_id,
        role_id    = role_id,
        role_name  = payload.get("RoleName") or payload.get("role", ""),
        first_name = payload.get("FirstName", ""),
        last_name  = payload.get("LastName", ""),
        full_name  = payload.get("name", ""),
        tenant_id  = payload.get("TenantId", "1"),
    )


# ── Optional user (for public endpoints that can also serve logged-in users) ──

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[CurrentUser]:
    """Returns CurrentUser if token is present and valid, None otherwise."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ── Role-based authorization factory ─────────────────────────────────────────
# Usage:  Depends(require_roles(Roles.SUPER_ADMIN, Roles.ORDER_MANAGER))

def require_roles(*allowed_role_ids: int):
    """
    Dependency factory — enforces role-based access.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
        async def admin_endpoint():
            ...

        # Or with current_user injection:
        @router.get("/orders")
        async def list_orders(user = Depends(require_roles(Roles.SUPER_ADMIN, Roles.ORDER_MANAGER))):
            ...
    """
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


# ── Convenience shortcuts ─────────────────────────────────────────────────────

def require_super_admin():
    """Only SuperAdmin (RoleId=1)."""
    return require_roles(Roles.SUPER_ADMIN)


def require_staff():
    """Any staff role (SuperAdmin, InventoryManager, ProductManager, OrderManager, CustomerSupport)."""
    return require_roles(*Roles.STAFF)


def require_admin_or_order_manager():
    """SuperAdmin or OrderManager — e.g. for order management endpoints."""
    return require_roles(Roles.SUPER_ADMIN, Roles.ORDER_MANAGER)


def require_inventory_access():
    """SuperAdmin, InventoryManager, or ProductManager."""
    return require_roles(Roles.SUPER_ADMIN, Roles.INVENTORY_MANAGER, Roles.PRODUCT_MANAGER)