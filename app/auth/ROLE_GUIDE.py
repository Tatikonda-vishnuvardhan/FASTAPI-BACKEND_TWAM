"""
TWAM ROLE-BASED ACCESS CONTROL REFERENCE
=========================================

How to add role restrictions to any endpoint in your routes.py files.

ROLE IDs (from TWAMConstants.RoleConstants / AuthenticationConstants.RoleConstants):
  1 = Super Admin
  2 = User / Customer
  3 = Inventory Manager
  4 = Product Manager
  5 = Order Manager
  6 = Customer Support

═══════════════════════════════════════════════════════════════
IMPORT PATTERN
═══════════════════════════════════════════════════════════════

from ..auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

═══════════════════════════════════════════════════════════════
USAGE PATTERN 1 — route-level (just enforce access, no user object needed)
═══════════════════════════════════════════════════════════════

@router.delete("/{id}", dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
async def delete_item(id: int, db: Session = Depends(get_db)):
    ...

═══════════════════════════════════════════════════════════════
USAGE PATTERN 2 — inject current user + enforce role
═══════════════════════════════════════════════════════════════

@router.post("/")
async def create_item(
    data: ItemCreate,
    current_user: CurrentUser = Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER)),
    db: Session = Depends(get_db),
):
    # current_user.user_id, current_user.role_id, current_user.email all available
    ...

═══════════════════════════════════════════════════════════════
USAGE PATTERN 3 — read current user without role enforcement
═══════════════════════════════════════════════════════════════

@router.get("/my-orders")
async def my_orders(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Filter data by current_user.user_id
    ...

═══════════════════════════════════════════════════════════════
RECOMMENDED ROLE MATRIX (apply to each module's routes.py)
═══════════════════════════════════════════════════════════════

MODULE            | LIST/GET             | CREATE               | UPDATE               | DELETE
──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────
address           | User (own only)      | User                 | User (own only)      | User (own only)
blog              | All authenticated    | SuperAdmin           | SuperAdmin           | SuperAdmin
brand             | All authenticated    | SuperAdmin, ProdMgr  | SuperAdmin, ProdMgr  | SuperAdmin
cart              | User (own only)      | User                 | User (own only)      | User (own only)
category          | All authenticated    | SuperAdmin, ProdMgr  | SuperAdmin, ProdMgr  | SuperAdmin
common            | Staff only           | Staff only           | Staff only           | SuperAdmin
country           | All authenticated    | SuperAdmin           | SuperAdmin           | SuperAdmin
coupons           | Staff only           | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin
cupsize           | All authenticated    | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
deliverycharge    | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
email (sendmail)  | Staff only           | Staff only           | —                    | —
fabric            | All authenticated    | SuperAdmin, ProdMgr  | SuperAdmin, ProdMgr  | SuperAdmin
fileupload        | All authenticated    | All authenticated    | —                    | SuperAdmin
integrationloc    | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
invoice           | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin
mdm               | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
menu              | All authenticated    | SuperAdmin           | SuperAdmin           | SuperAdmin
menuroleclaim     | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
messagetemplate   | Staff only           | SuperAdmin, CustSup  | SuperAdmin, CustSup  | SuperAdmin
orderitems        | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin
orders            | User (own), Staff    | User                 | SuperAdmin, OrdMgr   | SuperAdmin
packagingtemplates| Staff only           | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
people            | Staff only           | SuperAdmin           | SuperAdmin, User(own)| SuperAdmin
productreview     | All authenticated    | User                 | User (own only)      | SuperAdmin
products          | All authenticated    | SuperAdmin, ProdMgr  | SuperAdmin, ProdMgr  | SuperAdmin
productvariant    | All authenticated    | SuperAdmin, ProdMgr  | SuperAdmin, ProdMgr  | SuperAdmin
productvariantdetail| All authenticated  | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
report            | SuperAdmin, Staff    | —                    | —                    | —
shipment          | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin, OrdMgr   | SuperAdmin
shippingtype      | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
size              | All authenticated    | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
state             | All authenticated    | SuperAdmin           | SuperAdmin           | SuperAdmin
stores            | All authenticated    | SuperAdmin           | SuperAdmin           | SuperAdmin
supplierinfo      | Staff only           | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
supportrequest    | CustSup, OrdMgr, SA  | User                 | CustSup, SA          | SuperAdmin
taxhsncode        | Staff only           | SuperAdmin, InvMgr   | SuperAdmin, InvMgr   | SuperAdmin
userdashboard     | User (own data)      | —                    | —                    | —
userrole          | Staff only           | SuperAdmin           | SuperAdmin           | SuperAdmin
userreview        | All authenticated    | User                 | User (own only)      | SuperAdmin
wishlist          | User (own only)      | User                 | User (own only)      | User (own only)

Legend:
  SA       = Roles.SUPER_ADMIN (1)
  User     = Roles.USER (2)
  InvMgr   = Roles.INVENTORY_MANAGER (3)
  ProdMgr  = Roles.PRODUCT_MANAGER (4)
  OrdMgr   = Roles.ORDER_MANAGER (5)
  CustSup  = Roles.CUSTOMER_SUPPORT (6)
  Staff    = All roles except User: (1,3,4,5,6)

═══════════════════════════════════════════════════════════════
DATA FILTERING PATTERN (user sees only their own data)
═══════════════════════════════════════════════════════════════

Example: orders/routes.py — user gets only their orders, admin gets all

@router.get("/")
async def list_orders(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role_id == Roles.USER:
        # Filter by UserProfileId = current_user.user_id
        return repo.get_orders_by_user(db, current_user.user_id)
    elif current_user.role_id in (Roles.SUPER_ADMIN, Roles.ORDER_MANAGER):
        return repo.get_all_orders(db)
    else:
        raise HTTPException(403, "Access denied.")

═══════════════════════════════════════════════════════════════
QUICK REFERENCE — convenience helpers in dependencies.py
═══════════════════════════════════════════════════════════════

require_super_admin()             → RoleId = 1 only
require_staff()                   → RoleId in {1,3,4,5,6} (not User)
require_admin_or_order_manager()  → RoleId in {1,5}
require_inventory_access()        → RoleId in {1,3,4}
require_roles(1, 5)               → any combination you choose
"""