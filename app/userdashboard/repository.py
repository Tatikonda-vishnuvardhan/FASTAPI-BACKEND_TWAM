import os
from sqlalchemy.orm import Session
from sqlalchemy import text

BASE_URL = os.getenv("BASE_URL", "")

def _get_variant_image(db: Session, product_variant_id: int) -> str:
    try:
        row = db.execute(text(
            'SELECT CONCAT(:base, "FilePath") FROM twam."ProductImage" '
            'WHERE "ProductVariantId"=:vid AND "DeletedInd"=false AND "FilePath" IS NOT NULL LIMIT 1'
        ), {"base": BASE_URL, "vid": product_variant_id}).fetchone()
        return row[0] if row else None
    except Exception:
        return None

def _get_variant_pricing(db: Session, product_variant_id: int) -> tuple:
    try:
        row = db.execute(text(
            'SELECT "FinalPrice", "MRPPrice" FROM twam."ProductVariantDetail" '
            'WHERE "ProductVariantId"=:vid LIMIT 1'
        ), {"vid": product_variant_id}).fetchone()
        return (float(row[0]) if row and row[0] else None,
                float(row[1]) if row and row[1] else None)
    except Exception:
        return (None, None)

def _get_avg_rating(db: Session, product_variant_id: int) -> float:
    try:
        row = db.execute(text(
            'SELECT AVG("Rating"::numeric) FROM twam."ProductReview" '
            'WHERE "ProductVariantId"=:vid AND "DeletedInd"=false'
        ), {"vid": product_variant_id}).fetchone()
        return round(float(row[0]), 2) if row and row[0] else 0.0
    except Exception:
        return 0.0

def get_dashboard(db: Session, user_profile_id: str) -> dict:
    cart_count = 0
    wishlist_count = 0
    wishlist_items = []
    best_sellers = []
    new_arrivals = []

    # Cart count
    try:
        row = db.execute(text(
            'SELECT COUNT(*) FROM twam."Cart" WHERE "DeletedInd"=false AND "UserProfileId"=:uid AND "IsOrdered" IS NOT TRUE'
        ), {"uid": user_profile_id}).fetchone()
        cart_count = int(row[0]) if row else 0
    except Exception:
        pass

    # Wishlist count + items
    try:
        rows = db.execute(text(
            'SELECT "ProductId","ProductVariantId","ProductVariantDetailId" FROM twam."Wishlist" '
            'WHERE "DeletedInd"=false AND "UserProfileId"=:uid'
        ), {"uid": user_profile_id}).fetchall()
        wishlist_count = len(rows)
        wishlist_items = [{"productId": r[0], "productVariantId": r[1], "productVariantDetailId": r[2]} for r in rows]
    except Exception:
        pass

    # Best sellers
    try:
        rows = db.execute(text(
            'SELECT pv."ProductVariantId", pv."ProductId", p."Name", pv."VariantDescription" '
            'FROM twam."ProductVariants" pv '
            'LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId" '
            'WHERE pv."DeletedInd"=false AND pv."IsBestSeller"=true '
            'ORDER BY pv."CreatedDate" DESC LIMIT 12'
        )).fetchall()
        for r in rows:
            vid = r[0]
            price, old_price = _get_variant_pricing(db, vid)
            best_sellers.append({
                "productId": r[1], "productVariantId": vid,
                "name": r[2], "description": r[3],
                "price": price, "oldPrice": old_price,
                "image": _get_variant_image(db, vid),
                "rating": _get_avg_rating(db, vid),
                "bestseller": True, "color": None
            })
    except Exception:
        pass

    # New arrivals
    try:
        rows = db.execute(text(
            'SELECT pv."ProductVariantId", pv."ProductId", p."Name", pv."VariantDescription" '
            'FROM twam."ProductVariants" pv '
            'LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId" '
            'WHERE pv."DeletedInd"=false '
            'ORDER BY pv."CreatedDate" DESC LIMIT 12'
        )).fetchall()
        for r in rows:
            vid = r[0]
            price, old_price = _get_variant_pricing(db, vid)
            new_arrivals.append({
                "productId": r[1], "productVariantId": vid,
                "name": r[2], "description": r[3],
                "price": price, "oldPrice": old_price,
                "image": _get_variant_image(db, vid),
                "rating": _get_avg_rating(db, vid),
                "bestseller": True, "color": None
            })
    except Exception:
        pass

    return {
        "cartCount": cart_count,
        "wishlistCount": wishlist_count,
        "bestSellers": best_sellers,
        "newArrivals": new_arrivals,
        "wishlistItems": wishlist_items
    }

def get_product_messages(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    """Returns product message list using MessageConfiguration table."""
    try:
        rows = db.execute(text(
            'SELECT "MessageConfigurationId", "MessageType", "MessageContent", "CreatedDate" '
            'FROM mdm."MessageConfiguration" WHERE "DeletedInd"=false ORDER BY "CreatedDate" DESC'
        )).fetchall()
        result = [{"messageConfigurationId": r[0], "messageType": r[1], "messageContent": r[2], "createdDate": r[3]} for r in rows]
        return {"count": len(result), "list": result, "parameters": None}
    except Exception:
        return {"count": 0, "list": [], "parameters": None}