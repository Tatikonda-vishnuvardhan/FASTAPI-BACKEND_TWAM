import os
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Wishlist

BASE_URL = os.getenv("BASE_URL", "")

def _enrich(db: Session, w: Wishlist) -> dict:
    image = None
    product_name = None
    variant_name = None
    final_price = None
    mrp_price = None
    size_label = None
    try:
        row = db.execute(text("""
            SELECT p."Name", pv."VariantName", pvd."FinalPrice", pvd."MRPPrice", s."SizeLabel",
                   (SELECT CONCAT(:base, pi2."FilePath") FROM twam."ProductImage" pi2
                    WHERE pi2."ProductVariantId" = :vid AND pi2."DeletedInd"=false
                    AND pi2."FilePath" IS NOT NULL LIMIT 1)
            FROM twam."Products" p
            LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = :vid
            LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantId" = :vid
            LEFT JOIN mdm."Size" s ON s."SizeId" = pvd."Size"
            WHERE p."ProductId" = :pid LIMIT 1
        """), {"pid": w.productId, "vid": w.productVariantId, "base": BASE_URL}).fetchone()
        if row:
            product_name, variant_name = row[0], row[1]
            final_price = float(row[2]) if row[2] else None
            mrp_price = float(row[3]) if row[3] else None
            size_label, image = row[4], row[5]
    except Exception:
        pass
    return {"wishlistId": w.wishlistId, "productId": w.productId, "productVariantId": w.productVariantId,
            "productVariantDetailId": w.productVariantDetailId, "userProfileId": w.userProfileId,
            "state": w.state, "imageURL": image, "productName": product_name, "variantName": variant_name,
            "finalPrice": final_price, "mrpPrice": mrp_price, "sizeLabel": size_label, "createdDate": w.createdDate}

def get_all(db, filters, order_ascending, order_property, page_index, page_size):
    base_sql = """
        SELECT
            w."WishlistId"              AS wishlistId,
            w."ProductId"               AS productId,
            w."ProductVariantId"        AS productVariantId,
            w."ProductVariantDetailId"  AS productVariantDetailId,
            w."UserProfileId"           AS userProfileId,
            w."State"                   AS state,

            p."Name"                    AS productName,
            pv."VariantName"            AS variantName,

            pvd."FinalPrice"  AS finalPrice,
            pvd."MRPPrice"    AS mrpPrice,
            pv."Color"        AS color,

            -- Get first image from ProductImage table
            (SELECT pi2."FilePath"
             FROM twam."ProductImage" pi2
             WHERE pi2."ProductVariantId" = w."ProductVariantId"
               AND pi2."DeletedInd" = false
               AND pi2."FilePath" IS NOT NULL
             ORDER BY pi2."CreatedDate"
             LIMIT 1) AS imageURL

        FROM twam."Wishlist" w
        LEFT JOIN twam."ProductVariants" pv
               ON pv."ProductVariantId" = w."ProductVariantId"
        LEFT JOIN twam."ProductVariantDetail" pvd
               ON pvd."ProductVariantDetailId" = COALESCE(
                   w."ProductVariantDetailId",
                   (SELECT pvd2."ProductVariantDetailId"
                    FROM twam."ProductVariantDetail" pvd2
                    WHERE pvd2."ProductVariantId" = w."ProductVariantId"
                      AND pvd2."DeletedInd" = false
                    ORDER BY pvd2."ProductVariantDetailId"
                    LIMIT 1)
               )
        LEFT JOIN twam."Products" p
               ON p."ProductId" = w."ProductId"
        WHERE w."DeletedInd" = false
    """

    # Apply filters
    params = {}
    if filters:
        for f in filters:
            if f["property"] == "userProfileId":
                base_sql += ' AND w."UserProfileId" = :uid'
                params["uid"] = f["value"]

    base_sql += ' ORDER BY w."CreatedDate" DESC'

    rows = db.execute(text(base_sql), params).fetchall()

    results = []
    for r in rows:
        raw = dict(r._mapping) if hasattr(r, '_mapping') else dict(r)

        def g(key: str):
            """Case-insensitive get from the raw row dict."""
            return raw.get(key) or raw.get(key.lower()) or raw.get(key.upper())

        img = g('imageURL') or g('imageurl') or ''
        if img and not img.startswith('http'):
            img = BASE_URL.rstrip('/') + '/' + img.lstrip('/')

        results.append({
            'wishlistId':             g('wishlistId'),
            'productId':              g('productId'),
            'productVariantId':       g('productVariantId'),
            'productVariantDetailId': g('productVariantDetailId'),
            'userProfileId':          g('userProfileId'),
            'state':                  g('state'),
            'productName':            g('productName'),
            'variantName':            g('variantName'),
            'finalPrice':             float(g('finalPrice')) if g('finalPrice') is not None else None,
            'mrpPrice':               float(g('mrpPrice'))   if g('mrpPrice')   is not None else None,
            'imageURL':               img,
            'color':                  g('color'),
            'sizeLabel':              g('sizeLabel'),
            'createdDate':            g('createdDate'),
        })
    
    print(f"✅ Wishlist: Retrieved {len(results)} items for filters {params}")
    return {
        "count": len(results),
        "list": results
    }

# ── Create Wishlist — IMPROVED VERSION ───────────────────────────────────────

def create(db: Session, data) -> Dict:
    """
    IMPROVED: Returns dict with status info instead of just ID.
    
    If same variant already in wishlist for user → return existing.
    Otherwise → create new wishlist item.
    
    Returns: {"wishlistId": int, "status": "created"|"existing"}
    """
    # If same variant already in wishlist for user, return existing
    existing = db.query(Wishlist).filter(
        Wishlist.productVariantId == data.productVariantId,
        Wishlist.userProfileId == data.userProfileId,
        Wishlist.deletedInd == False
    ).first()
    
    if existing:
        print(f"⊘ Wishlist: Item already exists - wishlistId {existing.wishlistId}")
        return {
            "wishlistId": existing.wishlistId,
            "status": "existing",
            "message": "Item already in wishlist"
        }
    
    # Create new
    entity = Wishlist(
        productId=data.productId,
        productVariantId=data.productVariantId,
        productVariantDetailId=data.productVariantDetailId,
        userProfileId=data.userProfileId,
        state=data.state or "Active",
        createdDate=datetime.now(timezone.utc),
        deletedInd=False
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    
    print(f"✅ Wishlist: Created new item - wishlistId {entity.wishlistId}")
    return {
        "wishlistId": entity.wishlistId,
        "status": "created",
        "message": "Item added to wishlist"
    }

# ── Bulk Create Wishlist — IMPROVED VERSION ──────────────────────────────────

def create_bulk(db: Session, items: list, user_profile_id: str) -> Dict:
    """
    IMPROVED: Returns detailed sync statistics.
    
    For each item: if variant already in wishlist → skip.
    Otherwise → add new.
    
    Returns: {
        "success": True,
        "added": int,      # New items created
        "skipped": int,    # Items already in wishlist
        "total": int       # Total items processed
    }
    """
    added_count = 0
    skipped_count = 0
    new_items = []
    
    print(f"🔄 Wishlist: Processing bulk sync for user {user_profile_id} - {len(items)} items")
    
    # Fetch all existing wishlist items for this user in one query (efficient)
    existing_variants = db.query(Wishlist.productVariantId).filter(
        Wishlist.userProfileId == user_profile_id,
        Wishlist.deletedInd == False
    ).all()
    existing_variant_ids = {v[0] for v in existing_variants}
    
    print(f"  📋 User has {len(existing_variant_ids)} existing wishlist items")
    
    # Process each item
    for item in items:
        if item.productVariantId in existing_variant_ids:
            # Already exists
            skipped_count += 1
            print(f"  ⊘ Skipped variant {item.productVariantId}: already in wishlist")
        else:
            # Add to batch for bulk insert
            new_item = Wishlist(
                productId=item.productId,
                productVariantId=item.productVariantId,
                productVariantDetailId=item.productVariantDetailId,
                userProfileId=user_profile_id,
                state=item.state or "Active",
                createdDate=datetime.now(timezone.utc),
                deletedInd=False
            )
            new_items.append(new_item)
            existing_variant_ids.add(item.productVariantId)  # Track to prevent duplicates within batch
            added_count += 1
    
    # Bulk insert new items (more efficient than individual inserts)
    if new_items:
        db.bulk_save_objects(new_items)
        print(f"  + Added {len(new_items)} new wishlist items in bulk")
    
    # Single commit for all changes
    db.commit()
    
    result = {
        "success": True,
        "added": added_count,
        "skipped": skipped_count,
        "total": len(items),
        "message": f"Synced {added_count} items ({added_count} new, {skipped_count} already existed)"
    }
    
    print(f"✅ Wishlist: Bulk sync complete - {result['message']}")
    return result

def delete(db: Session, wishlist_id: int) -> bool:
    entity = db.query(Wishlist).filter(Wishlist.wishlistId == wishlist_id).first()
    if not entity:
        return False
    entity.deletedInd = True
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    print(f"✅ Wishlist: Deleted item {wishlist_id}")
    return True

def delete_by_variant(db: Session, product_variant_id: int) -> bool:
    entities = db.query(Wishlist).filter(
        Wishlist.productVariantId == product_variant_id,
        Wishlist.deletedInd == False
    ).all()
    if not entities:
        return False
    for e in entities:
        e.deletedInd = True
        e.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    print(f"✅ Wishlist: Deleted {len(entities)} items for variant {product_variant_id}")
    return True

def create_for_guest(db: Session, data) -> Dict:
    """
    IMPROVED: Same as create but allows guest flow.
    Returns dict with status info.
    """
    # Prevent duplicate even for guest
    existing = db.query(Wishlist).filter(
        Wishlist.productVariantId == data.productVariantId,
        Wishlist.userProfileId == data.userProfileId,
        Wishlist.deletedInd == False
    ).first()
    
    if existing:
        print(f"⊘ Wishlist (Guest): Item already exists - wishlistId {existing.wishlistId}")
        return {
            "wishlistId": existing.wishlistId,
            "status": "existing",
            "message": "Item already in wishlist"
        }

    entity = Wishlist(
        productId=data.productId,
        productVariantId=data.productVariantId,
        productVariantDetailId=data.productVariantDetailId,
        userProfileId=data.userProfileId,
        state=data.state or "Active",
        createdDate=datetime.now(timezone.utc),
        deletedInd=False
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    
    print(f"✅ Wishlist (Guest): Created new item - wishlistId {entity.wishlistId}")
    return {
        "wishlistId": entity.wishlistId,
        "status": "created",
        "message": "Item added to wishlist"
    }


def get_user_wishlist(db: Session, user_id: str):
    sql = """
        SELECT 
            w."WishlistId",
            w."ProductId",
            w."ProductVariantId",
            w."ProductVariantDetailId",

            p."Name" AS productName,
            pv."VariantName" AS variantName,

            pvd."FinalPrice",
            pvd."MRPPrice",
            pvd."DiscountPercent",
            sz."SizeLabel",
            pv."Color",

            (
                SELECT pi."FilePath"
                FROM twam."ProductImage" pi
                WHERE 
                    pi."ProductVariantId" = w."ProductVariantId"
                    AND (pi."DeletedInd" = false OR pi."DeletedInd" IS NULL)
                ORDER BY pi."ProductImageId"
                LIMIT 1
            ) AS imageURL

        FROM twam."Wishlist" w
        LEFT JOIN twam."Products" p 
               ON p."ProductId" = w."ProductId"
        LEFT JOIN twam."ProductVariants" pv 
               ON pv."ProductVariantId" = w."ProductVariantId"
        LEFT JOIN twam."ProductVariantDetail" pvd 
               ON pvd."ProductVariantDetailId" = w."ProductVariantDetailId"
        LEFT JOIN mdm."Size" sz
               ON sz."SizeId" = pvd."Size"

        WHERE w."UserProfileId" = :uid AND w."DeletedInd" = false
        ORDER BY w."CreatedDate" DESC;
    """

    rows = db.execute(text(sql), {"uid": user_id}).fetchall()
    results = [dict(r._mapping) for r in rows]
    
    print(f"✅ Wishlist: Retrieved {len(results)} items for user {user_id}")
    return results