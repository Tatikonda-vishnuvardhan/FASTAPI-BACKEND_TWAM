import os
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import Cart

BASE_URL = os.getenv("BASE_URL", "")

# ── Get Cart List ─────────────────────────────────────────────────────────────

def get_cart_list(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    # Build base query with all joins via raw SQL to match .NET handler exactly
    sql = f"""
        SELECT
            c."CartId",
            c."ProductId",
            c."ProductVariantId",
            c."ProductVariantDetailId",
            p."ProductCode",
            p."Name"            AS product_name,
            p."Description"     AS product_description,
            b."brandName"       AS brand_name,
            p."CategoryId",
            p."BrandId",
            pv."VariantName",
            pv."VariantDescription",
            s."SizeLabel"       AS size,
            cs."SizeLabel"      AS cup_size,
            pv."Color",
            pvd."AvailableQuantity"  AS stock_quantity,
            c."Quantity"        AS processed_quantity,
            pvd."ReturnedQuantity",
            pvd."DiscountPercent",
            pvd."MRPPrice",
            pvd."FinalPrice",
            pvd."TaxAmount",
            c."PersonalId",
            c."UserProfileId",
            c."State",
            c."CreatedDate",
            c."ModifiedDate",
            (
                SELECT CONCAT('{BASE_URL}', pi2."FilePath")
                FROM twam."ProductImage" pi2
                WHERE pi2."ProductVariantId" = c."ProductVariantId"
                  AND pi2."DeletedInd" = false
                  AND pi2."FilePath" IS NOT NULL
                  AND pi2."FilePath" != ''
                LIMIT 1
            ) AS image
        FROM twam."Cart" c
        LEFT JOIN twam."Products"             p   ON p."ProductId"               = c."ProductId"
        LEFT JOIN mdm."brands"                b   ON b."brandId"                 = p."BrandId"
        LEFT JOIN twam."ProductVariants"      pv  ON pv."ProductVariantId"       = c."ProductVariantId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = c."ProductVariantDetailId"
        LEFT JOIN mdm."Size"                  s   ON s."SizeId"                  = pvd."Size"
        LEFT JOIN mdm."CupSize"               cs  ON cs."CupSizeId"              = pvd."CupSize"
        WHERE c."DeletedInd" = false AND (c."IsOrdered" IS NULL OR c."IsOrdered" = false)
    """

    # Apply filters
    where_clauses = []
    params = {}
    if filters:
        for i, f in enumerate(filters):
            prop = f.get("property", "")
            comparison = f.get("comparison", "eq").lower()
            value = f.get("value")

            col_map = {
                "userProfileId": 'c."UserProfileId"',
                "productId":     'c."ProductId"',
                "state":         'c."State"',
                "productName":   'p."Name"',
                "brandName":     'b."brandName"',
            }
            col = col_map.get(prop)
            if col and value is not None:
                param_key = f"param_{i}"
                if comparison == "eq":
                    where_clauses.append(f"{col} = :{param_key}")
                elif comparison == "neq":
                    where_clauses.append(f"{col} != :{param_key}")
                elif comparison == "contains":
                    where_clauses.append(f"{col} ILIKE :{param_key}")
                    value = f"%{value}%"
                elif comparison == "startswith":
                    where_clauses.append(f"{col} ILIKE :{param_key}")
                    value = f"{value}%"
                params[param_key] = value

    if where_clauses:
        sql += " AND " + " AND ".join(where_clauses)

    # Order
    order_col_map = {
        "productName":  'p."Name"',
        "createdDate":  'c."CreatedDate"',
        "modifiedDate": 'c."ModifiedDate"',
        "finalPrice":   'pvd."FinalPrice"',
    }
    if order_property and order_property in order_col_map:
        direction = "ASC" if order_ascending is not False else "DESC"
        sql += f" ORDER BY {order_col_map[order_property]} {direction}"

    # Count
    count_sql = f"SELECT COUNT(*) FROM ({sql}) AS sub"
    total = db.execute(text(count_sql), params).scalar()

    # Pagination
    if page_index and page_size:
        sql += f" OFFSET {(page_index - 1) * page_size} LIMIT {page_size}"

    rows = db.execute(text(sql), params).fetchall()

    result = []
    for r in rows:
        result.append({
            "cartId":                r[0],
            "productId":             r[1],
            "productVariantId":      r[2],
            "productVariantDetailId":r[3],
            "productCode":           r[4],
            "productName":           r[5],
            "productDescription":    r[6],
            "brandName":             r[7],
            "categoryId":            r[8],
            "brandId":               r[9],
            "variantName":           r[10],
            "variantDescription":    r[11],
            "size":                  r[12],
            "cupSize":               r[13],
            "color":                 r[14],
            "stockQuantity":         r[15],
            "processedQuantity":     r[16],
            "returnedQuantity":      r[17],
            "discountPercent":       r[18],
            "mrpPrice":              float(r[19]) if r[19] else None,
            "finalPrice":            float(r[20]) if r[20] else None,
            "taxAmount":             float(r[21]) if r[21] else None,
            "personalId":            r[22],
            "userProfileId":         r[23],
            "state":                 r[24],
            "createdDate":           r[25],
            "modifiedDate":          r[26],
            "image":                 r[27] or "",
            "quantity":              r[16],  # processedQuantity = cart quantity
        })

    return build_paged_response(total, result)


# ── Create Cart — IMPROVED VERSION ───────────────────────────────────────────

def create_cart(db: Session, data) -> dict:
    """
    IMPROVED: Returns dict with status info instead of just ID.
    
    If the same productVariantDetailId already exists in cart for this user
    (not ordered, not deleted) → increment quantity and return 'updated'.
    Otherwise → create new cart item and return 'created'.
    
    Returns: {"cartId": int, "status": "created"|"updated", "quantity": int}
    """
    existing = db.query(Cart).filter(
        Cart.productVariantDetailId == data.productVariantDetailId,
        Cart.userProfileId == data.userProfileId,
        Cart.deletedInd == False,
        Cart.isOrdered != True
    ).first()

    if existing:
        # Update existing
        old_qty = existing.quantity or 0
        existing.quantity = old_qty + (data.quantity or 1)
        existing.modifiedDate = datetime.now(timezone.utc)
        db.commit()
        print(f"✅ Cart: Updated item {existing.cartId} - qty {old_qty} → {existing.quantity}")
        return {
            "cartId": existing.cartId,
            "status": "updated",
            "quantity": existing.quantity,
            "message": "Item quantity updated"
        }
    else:
        # Create new
        cart = Cart(
            personalId=data.personalId,
            productId=data.productId,
            productVariantDetailId=data.productVariantDetailId,
            productVariantId=data.productVariantId,
            userProfileId=data.userProfileId,
            quantity=data.quantity or 1,
            state=data.state or "Active",
            createdDate=datetime.now(timezone.utc),
            deletedInd=False,
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
        print(f"✅ Cart: Created new item {cart.cartId} - qty {cart.quantity}")
        return {
            "cartId": cart.cartId,
            "status": "created",
            "quantity": cart.quantity,
            "message": "Item added to cart"
        }


# ── Bulk Create Cart — IMPROVED VERSION ──────────────────────────────────────

def create_bulk_cart(db: Session, items: list, user_profile_id: str) -> Dict:
    """
    IMPROVED: Returns detailed sync statistics.
    
    For each item: if variant already in cart → increment qty.
    Otherwise → add new.
    
    Returns: {
        "success": True,
        "added": int,      # New items created
        "updated": int,    # Existing items quantity updated
        "skipped": int,    # Items already in cart with same qty
        "total": int       # Total items processed
    }
    """
    added_count = 0
    updated_count = 0
    skipped_count = 0
    new_carts = []

    print(f"🔄 Cart: Processing bulk sync for user {user_profile_id} - {len(items)} items")

    for item in items:
        # Check if item already exists
        existing = db.query(Cart).filter(
            Cart.productVariantDetailId == item.productVariantDetailId,
            Cart.userProfileId == user_profile_id,
            Cart.deletedInd == False,
            Cart.isOrdered != True
        ).first()

        if existing:
            # Update quantity
            old_qty = existing.quantity or 0
            new_qty = old_qty + (item.quantity or 1)
            
            if old_qty != new_qty:
                existing.quantity = new_qty
                existing.modifiedDate = datetime.now(timezone.utc)
                updated_count += 1
                print(f"  ↻ Updated cart item {existing.cartId}: qty {old_qty} → {new_qty}")
            else:
                skipped_count += 1
                print(f"  ⊘ Skipped cart item {existing.cartId}: same quantity")
        else:
            # Add to batch for bulk insert
            new_cart = Cart(
                personalId=item.personalId,
                productId=item.productId,
                productVariantDetailId=item.productVariantDetailId,
                productVariantId=item.productVariantId,
                userProfileId=user_profile_id,
                quantity=item.quantity or 1,
                state=item.state or "Active",
                createdDate=datetime.now(timezone.utc),
                deletedInd=False,
            )
            new_carts.append(new_cart)
            added_count += 1

    # Bulk insert new items (more efficient than individual inserts)
    if new_carts:
        db.bulk_save_objects(new_carts)
        print(f"  + Added {len(new_carts)} new cart items in bulk")

    # Single commit for all changes
    db.commit()

    result = {
        "success": True,
        "added": added_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(items),
        "message": f"Synced {added_count + updated_count} items ({added_count} new, {updated_count} updated, {skipped_count} skipped)"
    }

    print(f"✅ Cart: Bulk sync complete - {result['message']}")
    return result


# ── Update Cart ───────────────────────────────────────────────────────────────

def update_cart(db: Session, cart_id: int, quantity: int, user_profile_id: str, is_staff: bool = False) -> Optional[int]:
    query = db.query(Cart).filter(Cart.cartId == cart_id)
    if not is_staff:
        query = query.filter(Cart.userProfileId == user_profile_id)
    cart = query.first()
    if not cart:
        return None
    cart.quantity = quantity
    cart.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    print(f"✅ Cart: Updated item {cart_id} quantity to {quantity}")
    return cart.cartId


# ── Delete Cart (single) ──────────────────────────────────────────────────────

def delete_cart(db: Session, cart_id: int, user_profile_id: str, is_staff: bool = False) -> bool:
    query = db.query(Cart).filter(Cart.cartId == cart_id)
    if not is_staff:
        query = query.filter(Cart.userProfileId == user_profile_id)
    cart = query.first()
    if not cart:
        return False
    cart.deletedInd = True
    cart.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    print(f"✅ Cart: Deleted item {cart_id}")
    return True


# ── Delete Cart (multiple) ────────────────────────────────────────────────────

def delete_multiple_carts(db: Session, ids: List[int], user_profile_id: str, is_staff: bool = False) -> bool:
    query = db.query(Cart).filter(Cart.cartId.in_(ids))
    if not is_staff:
        query = query.filter(Cart.userProfileId == user_profile_id)
    carts = query.all()
    if not carts:
        return False
    for cart in carts:
        cart.deletedInd = True
        cart.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    print(f"✅ Cart: Deleted {len(carts)} items")
    return True
