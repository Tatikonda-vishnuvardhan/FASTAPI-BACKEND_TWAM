"""
main.py
────────
FastAPI application entry point.

Changes from original:
  - CORS allow_origins now read from settings (CORS_ORIGINS env var)
    instead of hardcoded ["*"]
  - Schema creation moved to @app.on_event("startup") — not on import
  - Base.metadata.create_all also in startup (dev only)
  - Removed unused OAuth2PasswordBearer import from top level
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import Base, engine, create_schemas, run_migrations

# ── Models (keep imports so create_all picks them up) ─────────────────────────
from app.address.models              import Address
from app.blog.models                 import Blog
from app.brand.models                import Brand
from app.cart.models                 import Cart
from app.category.models             import Category
from app.common.models               import ProductAudit, ProductVariantAudit, ProductVariantDetailAudit
from app.country.models              import Country
from app.coupons.models              import Coupons
from app.cupsize.models              import CupSize
from app.deliverycharge.models       import DeliveryCharge
from app.sendemail.models            import Email, EmailCredential
from app.fabric.models               import Fabric
from app.fileupload.models           import FileUpload
from app.integrationlocation.models  import IntegrationLocation
from app.invoice.models              import Invoice, InvoiceItem
from app.menu.models                 import Menu
from app.menuroleclaim.models        import MenuRoleClaim
from app.messagetemplate.models      import MessageTemplate
from app.orderitems.models           import OrderItems
from app.orders.models               import Orders, OrderTrackingStatus, OrderReturnInfo, OrderRefund
from app.packagingtemplates.models   import PackagingTemplates
from app.people.models               import People
from app.productreview.models        import ProductReview
from app.products.models             import Products
from app.productvariant.models       import ProductVariant, ProductImage
from app.productvariantdetail.models import ProductVariantDetail
from app.shipment.models             import Shipment
from app.shippingtype.models         import ShippingType
from app.size.models                 import Size
from app.state.models                import State
from app.stores.models               import Stores
from app.supplierinfo.models         import SupplierInfo
from app.supportrequest.models       import SupportRequest
from app.taxhsncode.models           import TaxHSNCode
from app.userrole.models             import UserRole
from app.userreview.models           import UserReview
from app.wishlist.models             import Wishlist
from app.newsletter.models           import Newsletter


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup/shutdown logic."""
    # Create schemas first, then tables
    create_schemas()
    Base.metadata.create_all(bind=engine)
    run_migrations()
    os.makedirs("uploads", exist_ok=True)
    # Auto-create ProductColor table and populate hex values on every startup
    from app.shared.color_init import init_product_color_table
    from database import SessionLocal
    db = SessionLocal()
    try:
        init_product_color_table(db)
    finally:
        db.close()
    yield
    # shutdown logic here if needed


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TWAM E-Commerce API",
    description="""
FastAPI backend — TWAM E-Commerce Platform.

## Authentication
All protected endpoints require a Bearer JWT token.

### How to get a token:
1. `POST /connect/token` with form: `grant_type=password`, `username`, `password`,
   `client_id=twam-web-portal`, `client_secret=twamsecret`
2. Copy `access_token` from response
3. Click **Authorize** above → paste the token

### Roles:
| ID | Name | Access |
|----|------|--------|
| 1 | Super Admin | Full access |
| 2 | User | Customer-facing endpoints |
| 3 | Inventory Manager | Products, stock |
| 4 | Product Manager | Products, categories |
| 5 | Order Manager | Orders, shipments |
| 6 | Customer Support | Orders, reviews, support |
    """,
    version="2.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins loaded from CORS_ORIGINS env var (comma-separated).
# For mobile (Capacitor): add "capacitor://localhost" to CORS_ORIGINS in .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers — Public ──────────────────────────────────────────────────────────
from app.auth.router                 import router as auth_router
from app.connect.router              import router as connect_router
from app.blog.router                 import router as blog_router
from app.brand.router                import router as brand_router
from app.category.router             import router as category_router
from app.coupons.router              import router as coupons_router
from app.deliverycharge.router       import router as deliverycharge_router
from app.mdm.router                  import router as mdm_router
from app.productvariant.router       import router as productvariant_router
from app.productvariantdetail.router import router as pvd_router
from app.userdashboard.router        import router as userdashboard_router
from app.userreview.router           import router as userreview_router
from app.sendemail.router            import router as email_router
from app.newsletter.router           import router as newsletter_router

# ── Routers — Protected ───────────────────────────────────────────────────────
from app.address.router              import router as address_router
from app.cart.router                 import router as cart_router
from app.common.router               import router as common_router
from app.country.router              import router as country_router
from app.cupsize.router              import router as cupsize_router
from app.fabric.router               import router as fabric_router
from app.fileupload.router           import router as fileupload_router
from app.integrationlocation.router  import router as integrationlocation_router
from app.invoice.router              import router as invoice_router
from app.menu.router                 import router as menu_router
from app.menuroleclaim.router        import router as menuroleclaim_router
from app.messagetemplate.router      import router as messagetemplate_router
from app.notification.router         import router as notification_router
from app.orderitems.router           import router as orderitems_router
from app.orders.router               import router as orders_router
from app.packagingtemplates.router   import router as packagingtemplates_router
from app.people.router               import router as people_router
from app.productreview.router        import router as productreview_router
from app.products.router             import router as products_router
from app.report.router               import router as report_router
from app.shipment.router             import router as shipment_router
from app.shippingtype.router         import router as shippingtype_router
from app.size.router                 import router as size_router
from app.state.router                import router as state_router
from app.stores.router               import router as stores_router
from app.supplierinfo.router         import router as supplierinfo_router
from app.supportrequest.router       import router as supportrequest_router
from app.taxhsncode.router           import router as taxhsncode_router
from app.userrole.router             import router as userrole_router
from app.wishlist.router             import router as wishlist_router

# ── Register all routers ──────────────────────────────────────────────────────
for router in (
    auth_router, connect_router, blog_router, brand_router, category_router,
    coupons_router, deliverycharge_router, mdm_router, productvariant_router,
    pvd_router, userdashboard_router, userreview_router, email_router,
    address_router, cart_router, common_router, country_router, cupsize_router,
    fabric_router, fileupload_router, integrationlocation_router, invoice_router,
    menu_router, menuroleclaim_router, messagetemplate_router, notification_router,
    orderitems_router, orders_router, packagingtemplates_router, people_router,
    productreview_router, products_router, report_router, shipment_router,
    shippingtype_router, size_router, state_router, stores_router,
    supplierinfo_router, supportrequest_router, taxhsncode_router,
    userrole_router, wishlist_router,
    newsletter_router,
):
    app.include_router(router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "TWAM E-Commerce API is running.", "docs": "/docs"}


app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")