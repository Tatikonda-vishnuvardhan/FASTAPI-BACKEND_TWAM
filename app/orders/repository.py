import os
import random
import json
import re
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text, asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import (
    Orders, OrderTrackingStatus,
    OrderReturnInfo, OrderRefund
)
from app.orderitems.models import OrderItems

BASE_URL = os.getenv("BASE_URL", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_order_number() -> str:
    return f"ORD{random.randint(1000, 9999)}"


def generate_order_item_number() -> str:
    return f"ORDI{random.randint(1000, 9999)}"


def _parse_min_order_value(order_value_range: Optional[str]) -> Optional[float]:
    if not order_value_range:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(order_value_range).replace(",", ""))
    return float(match.group(1)) if match else None


# apply_filters, apply_ordering, apply_pagination imported from app.shared.filters


def _get_address(db: Session, address_id):
    if not address_id:
        return None
    result = db.execute(
        text('SELECT "AddressId","AddressLine","City","PinCode","Phone","Name" FROM twam."Address" WHERE "AddressId" = :id AND "DeletedInd" = false'),
        {"id": address_id}
    ).fetchone()
    if result:
        return {
            "addressId": result[0], "addressLine": result[1],
            "city": result[2], "pinCode": result[3],
            "phone": result[4], "name": result[5]
        }
    return None


def _get_owned_address(db: Session, address_id: Optional[int], user_profile_id: Optional[str] = None):
    if not address_id:
        return None

    sql = 'SELECT "AddressId","UserProfileId","AddressLine","City","PinCode","Phone","Name" FROM twam."Address" WHERE "AddressId" = :id AND "DeletedInd" = false'
    params = {"id": address_id}

    if user_profile_id:
        sql += ' AND "UserProfileId" = :user_profile_id'
        params["user_profile_id"] = user_profile_id

    result = db.execute(text(sql), params).fetchone()
    if result:
        return {
            "addressId": result[0],
            "userProfileId": result[1],
            "addressLine": result[2],
            "city": result[3],
            "pinCode": result[4],
            "phone": result[5],
            "name": result[6],
        }
    return None


def _build_address_response(addr: Optional[dict]) -> Optional[dict]:
    if not addr:
        return None
    return {
        "addressId": addr.get("addressId"),
        "addressLine": addr.get("addressLine"),
        "city": addr.get("city"),
        "pinCode": addr.get("pinCode"),
        "phone": addr.get("phone"),
        "name": addr.get("name"),
    }


def _get_order_items_with_details(db: Session, order_ids: List[int], include_reviews: bool = False):
    if not order_ids:
        return []
    ids_str = ",".join(str(i) for i in order_ids)
    sql = f"""
        SELECT
            oi."OrderItemId", oi."OrderId", oi."ProductVariantDetailId",
            oi."ProductId", oi."ProductVariantId", oi."Quantity", oi."Price",
            oi."OrderItemNumber",
            p."Name" AS product_name,
            s."SizeLabel" AS size_label,
            cs."SizeLabel" AS cup_size_label,
            pv."Color" AS color,
            pv."IsReturnAvailable" AS is_return_available,
            (SELECT CONCAT('{BASE_URL}', pi2."FilePath")
             FROM twam."ProductImage" pi2
             WHERE pi2."ProductVariantId" = oi."ProductVariantId"
               AND pi2."DeletedInd" = false
               AND pi2."FilePath" IS NOT NULL
               AND pi2."FilePath" != ''
             LIMIT 1) AS product_image
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products" p ON p."ProductId" = oi."ProductId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
        LEFT JOIN mdm."Size" s ON s."SizeId" = pvd."Size"
        LEFT JOIN mdm."CupSize" cs ON cs."CupSizeId" = pvd."CupSize"
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = oi."ProductVariantId"
        WHERE oi."DeletedInd" = false AND oi."OrderId" IN ({ids_str})
    """
    rows = db.execute(text(sql)).fetchall()
    items = []
    for r in rows:
        items.append({
            "orderItemId": r[0], "orderId": r[1], "productVariantDetailId": r[2],
            "productId": r[3], "productVariantId": r[4], "quantity": r[5],
            "price": float(r[6]) if r[6] else None,
            "orderItemNumber": r[7], "productName": r[8],
            "size": r[9], "cupSize": r[10], "color": r[11],
            "isReturnAvailable": r[12], "productImage": r[13] or "",
            "rating": 0, "comment": None
        })

    if include_reviews and items:
        item_ids = [i["orderItemId"] for i in items]
        ids_str2 = ",".join(str(i) for i in item_ids)
        reviews = {
            r[0]: {"rating": r[1], "comment": r[2]}
            for r in db.execute(text(
                f'SELECT "ItemId","Rating","Comment" FROM twam."ProductReview" WHERE "ItemId" IN ({ids_str2})'
            )).fetchall()
        }
        for item in items:
            rev = reviews.get(item["orderItemId"])
            if rev:
                item["rating"] = rev["rating"] or 0
                item["comment"] = rev["comment"]
    return items


def _get_delivery_info(db: Session, shipping_type_id, order_subtotal: Optional[float] = None):
    if not shipping_type_id:
        return None
    row = db.execute(
        text('SELECT "DeliveryChargeId","DeliveryCharges","Days","IsFree","Description","OrderValueRange" FROM twam."DeliveryCharge" WHERE "ShippingTypeId" = :id AND "DeletedInd" = false LIMIT 1'),
        {"id": shipping_type_id}
    ).fetchone()
    if row:
        min_order_value = _parse_min_order_value(row[5])
        subtotal = float(order_subtotal or 0)
        is_eligible = min_order_value is None or subtotal >= min_order_value
        unlock_amount = round(max((min_order_value or 0) - subtotal, 0), 2) if min_order_value is not None else 0.0
        return {
            "deliveryChargeId": row[0],
            "deliveryCharges": float(row[1]) if row[1] is not None else None,
            "days": row[2],
            "isFree": row[3],
            "description": row[4],
            "orderValueRange": row[5],
            "minOrderValue": min_order_value,
            "isEligible": is_eligible,
            "unlockAmount": unlock_amount,
        }
    return None


def _normalize_order_addresses_and_delivery(db: Session, data):
    user_profile_id = getattr(data, "userProfileId", None)
    shipping_address_id = getattr(data, "shippingAddressId", None)
    billing_address_id = getattr(data, "billingAddressId", None) or shipping_address_id

    if shipping_address_id:
        shipping_address = _get_owned_address(db, shipping_address_id, user_profile_id)
        if not shipping_address:
            raise ValueError("Shipping address not found for this user.")
    else:
        shipping_address = None

    if billing_address_id:
        billing_address = _get_owned_address(db, billing_address_id, user_profile_id)
        if not billing_address:
            raise ValueError("Billing address not found for this user.")
    else:
        billing_address = shipping_address

    if getattr(data, "shippingTypeId", None):
        delivery_info = _get_delivery_info(
            db,
            getattr(data, "shippingTypeId", None),
            getattr(data, "subTotal", None),
        )
        if delivery_info and delivery_info.get("isEligible") is False:
            min_value = delivery_info.get("minOrderValue")
            raise ValueError(f"This shipping option is available only for orders above {min_value:.0f}.")
        if getattr(data, "deliveryCharge", None) is None and delivery_info and delivery_info.get("deliveryCharges") is not None:
            data.deliveryCharge = delivery_info["deliveryCharges"]

    data.shippingAddressId = shipping_address["addressId"] if shipping_address else None
    data.billingAddressId = billing_address["addressId"] if billing_address else None

    return shipping_address, billing_address


def _get_cart_checkout_items(db: Session, cart_ids: List[int], user_profile_id: str) -> List[dict]:
    if not cart_ids:
        return []

    ids_str = ",".join(str(int(cart_id)) for cart_id in cart_ids)
    rows = db.execute(text(f"""
        SELECT
            c."CartId",
            c."ProductId",
            c."ProductVariantId",
            c."ProductVariantDetailId",
            c."Quantity",
            p."Name",
            pvd."FinalPrice",
            pvd."TaxAmount",
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
        LEFT JOIN twam."Products" p ON p."ProductId" = c."ProductId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = c."ProductVariantDetailId"
        WHERE c."CartId" IN ({ids_str})
          AND c."UserProfileId" = :user_profile_id
          AND c."DeletedInd" = false
          AND (c."IsOrdered" IS NULL OR c."IsOrdered" = false)
    """), {"user_profile_id": user_profile_id}).fetchall()

    items = []
    for row in rows:
        quantity = int(row[4] or 0)
        unit_price = float(row[6]) if row[6] is not None else 0.0
        unit_tax = float(row[7]) if row[7] is not None else 0.0
        items.append({
            "cartId": row[0],
            "productId": row[1],
            "productVariantId": row[2],
            "productVariantDetailId": row[3],
            "quantity": quantity,
            "productName": row[5],
            "unitPrice": unit_price,
            "taxAmount": round(unit_tax * quantity, 2),
            "lineTotal": round(unit_price * quantity, 2),
            "productImage": row[8] or "",
        })
    return items


def get_checkout_summary(db: Session, user_profile_id: str, data) -> dict:
    if not user_profile_id:
        raise ValueError("User profile is required.")

    cart_ids = list(dict.fromkeys(data.cartIds or []))
    if not cart_ids:
        raise ValueError("At least one cart item is required.")

    shipping_address = _get_owned_address(db, data.shippingAddressId, user_profile_id) if data.shippingAddressId else None
    if data.shippingAddressId and not shipping_address:
        raise ValueError("Shipping address not found for this user.")

    billing_source_id = data.billingAddressId or data.shippingAddressId
    billing_address = _get_owned_address(db, billing_source_id, user_profile_id) if billing_source_id else shipping_address
    if billing_source_id and not billing_address:
        raise ValueError("Billing address not found for this user.")

    cart_items = _get_cart_checkout_items(db, cart_ids, user_profile_id)
    if len(cart_items) != len(cart_ids):
        raise ValueError("Some cart items were not found for this user.")

    sub_total = round(sum(item["lineTotal"] for item in cart_items), 2)
    tax_amount = round(sum(item["taxAmount"] for item in cart_items), 2)
    delivery_info = _get_delivery_info(db, data.shippingTypeId, sub_total)
    if delivery_info and delivery_info.get("isEligible") is False:
        min_value = delivery_info.get("minOrderValue")
        raise ValueError(f"This shipping option is available only for orders above {min_value:.0f}.")
    delivery_charge = round(float(delivery_info["deliveryCharges"]) if delivery_info and delivery_info.get("deliveryCharges") is not None else 0.0, 2)
    coupon_amount = round(float(data.couponAmount or 0), 2)
    total_amount = round(sub_total + delivery_charge - coupon_amount, 2)

    return {
        "shippingAddress": _build_address_response(shipping_address),
        "billingAddress": _build_address_response(billing_address),
        "deliveryInfo": delivery_info,
        "shippingTypeId": data.shippingTypeId,
        "cartItems": cart_items,
        "itemCount": len(cart_items),
        "totalQuantity": sum(item["quantity"] for item in cart_items),
        "subTotal": sub_total,
        "taxAmount": tax_amount,
        "deliveryCharge": delivery_charge,
        "couponAmount": coupon_amount,
        "totalAmount": total_amount,
    }


# ── Check Out of Stock ────────────────────────────────────────────────────────

def check_out_of_stock(db: Session, product_variant_detail_ids: List[int]) -> List[dict]:
    if not product_variant_detail_ids:
        return []
    ids_str = ",".join(str(i) for i in product_variant_detail_ids)
    try:
        rows = db.execute(
            text("CALL twam.SP_CheckProductStock(:ids)"),
            {"ids": ids_str}
        ).fetchall()
        return [{"productVariantDetailId": r[0], "productName": r[1]} for r in rows]
    except Exception:
        return []


# ── Create Order ──────────────────────────────────────────────────────────────

def create_order(db: Session, data) -> dict:
    # Accept both Pydantic model and dict
    if isinstance(data, dict):
        from types import SimpleNamespace
        data = SimpleNamespace(**data)
        data.orderItems = [
            SimpleNamespace(**i) if isinstance(i, dict) else i
            for i in (data.orderItems or [])
        ]

    order_items_input = data.orderItems or []
    if not order_items_input and getattr(data, "cartId", None):
        summary = get_checkout_summary(
            db,
            getattr(data, "userProfileId", None) or "",
            type("CheckoutPayload", (), {
                "cartIds": getattr(data, "cartId", None) or [],
                "shippingAddressId": getattr(data, "shippingAddressId", None),
                "billingAddressId": getattr(data, "billingAddressId", None),
                "shippingTypeId": getattr(data, "shippingTypeId", None),
                "couponAmount": getattr(data, "couponAmount", None) or 0,
            })()
        )
        if getattr(data, "subTotal", None) is None:
            data.subTotal = summary["subTotal"]
        if getattr(data, "taxAmount", None) is None:
            data.taxAmount = summary["taxAmount"]
        if getattr(data, "deliveryCharge", None) is None:
            data.deliveryCharge = summary["deliveryCharge"]
        if getattr(data, "totalAmount", None) is None:
            data.totalAmount = summary["totalAmount"]
        order_items_input = [
            type("OrderItem", (), {
                "productVariantDetailId": item["productVariantDetailId"],
                "productVariantId": item["productVariantId"],
                "productId": item["productId"],
                "quantity": item["quantity"],
                "price": item["unitPrice"],
            })()
            for item in summary["cartItems"]
        ]
        data.orderItems = order_items_input
    variant_ids = list({i.productVariantDetailId for i in order_items_input if i.productVariantDetailId})

    out_of_stock = check_out_of_stock(db, variant_ids)
    if out_of_stock:
        return {"outOfStockProducts": out_of_stock}

    _normalize_order_addresses_and_delivery(db, data)

    order = Orders(
        orderNumber=generate_order_number(),
        totalAmount=getattr(data, "totalAmount", None),
        orderDate=getattr(data, "orderDate", None) or datetime.now(timezone.utc),
        userProfileId=getattr(data, "userProfileId", None),
        state="Pending",
        createdDate=datetime.now(timezone.utc),
        deletedInd=False,
        shippingAddressId=getattr(data, "shippingAddressId", None),
        billingAddressId=getattr(data, "billingAddressId", None),
        personalId=0,
        couponId=getattr(data, "couponId", None),
        shippingTypeId=getattr(data, "shippingTypeId", None),
        couponAmount=getattr(data, "couponAmount", None),
        deliveryCharge=getattr(data, "deliveryCharge", None),
        taxAmount=getattr(data, "taxAmount", None),
        subTotal=getattr(data, "subTotal", None),
        isWhatsappNotification=getattr(data, "isWhatsappNotification", None),
        paymentMethod=getattr(data, "paymentMethod", None),
        paymentAccount=getattr(data, "paymentAccount", None),
        platform=getattr(data, "platform", None),
    )
    db.add(order)
    db.flush()  # get auto-generated orderId
    order_id = order.orderId

    # Fetch variant tax/price info
    pvd_map = {}
    if order_items_input:
        pvd_ids = [i.productVariantDetailId for i in order_items_input if i.productVariantDetailId]
        if pvd_ids:
            ids_str = ",".join(str(i) for i in pvd_ids)
            rows = db.execute(text(
                f'SELECT "ProductVariantDetailId","CGST","SGST","TaxAmount","FinalPrice" FROM twam."ProductVariantDetail" WHERE "ProductVariantDetailId" IN ({ids_str})'
            )).fetchall()
            pvd_map = {r[0]: {"cgst": r[1], "sgst": r[2], "taxAmount": r[3], "finalPrice": r[4]} for r in rows}

        for x in order_items_input:
            variant  = pvd_map.get(x.productVariantDetailId, {})
            tax      = float(variant.get("taxAmount") or 0)
            final_price = float(variant.get("finalPrice") or 0)

            # ── BUG FIX: OrderItems model uses PascalCase column names ──────
            item = OrderItems(
                OrderId                = order_id,
                OrderItemNumber        = generate_order_item_number(),
                ProductVariantDetailId = x.productVariantDetailId,
                ProductVariantId       = x.productVariantId,
                ProductId              = x.productId,
                Quantity               = x.quantity,
                Price                  = x.price,
                CreatedDate            = datetime.now(timezone.utc),
                DeletedInd             = False,
                TaxAmount              = tax,
                CGST                   = variant.get("cgst"),
                SGST                   = variant.get("sgst"),
                UnitPrice              = float(final_price) - float(tax) if final_price else None,
            )
            db.add(item)

    # Add initial tracking status
    db.add(OrderTrackingStatus(
        orderId=order_id,
        status="Pending",
        createdDate=datetime.now(timezone.utc)
    ))
    
    db.commit()

    # Mark cart items as ordered
    cart_ids = getattr(data, "cartId", None) or []
    user_profile_id = getattr(data, "userProfileId", None) or ""
    if cart_ids:
        ids_str = ",".join(str(i) for i in cart_ids)
        db.execute(text(
            f"UPDATE twam.\"Cart\" SET \"IsOrdered\" = true WHERE \"UserProfileId\" = '{user_profile_id}' AND \"CartId\" IN ({ids_str}) AND \"DeletedInd\" = false"
        ))
        db.commit()

    # Send order confirmation notification (email + SMS)
    try:
        from app.ekart.notifications import send_order_placed_notification
        send_order_placed_notification(db, order_id)
    except Exception as e:
        print(f"[Order] Notification failed for order {order_id}: {e}")

    # TODO: Integrate IPaymentService.CreateOrderRequestAsync
    return {"orderId": order_id, "paymentProcessUrl": None}


# ── ReOrder (Cart) ────────────────────────────────────────────────────────────

def reorder_from_cart(db: Session, order_id: int, user_profile_id: str) -> int:
    payload = json.dumps({"OrderId": str(order_id), "UserProfileId": user_profile_id})
    try:
        db.execute(text("CALL twam.SP_AutoCreateCart(:cart_search)"), {"cart_search": payload})
        db.commit()
    except Exception:
        db.rollback()
    return order_id


# ── Guest Order ───────────────────────────────────────────────────────────────

def create_guest_order(db: Session, data) -> dict:
    # TODO: Replace stub with IIdentityUserService.CreateIdentityUserAsync
    user_profile_id = getattr(data, "userProfileId", None) or f"guest_{random.randint(10000, 99999)}"

    order_items_input = data.orderItems or []
    variant_ids = list({i.productVariantDetailId for i in order_items_input if i.productVariantDetailId})
    out_of_stock = check_out_of_stock(db, variant_ids)
    if out_of_stock:
        return {"outOfStockProducts": out_of_stock}

    # Create address
    address = {
        "name": f"{data.firstName or ''} {data.lastName or ''}".strip(),
        "addressLine": data.addressLine, "locality": data.locality, "city": data.city,
        "stateId": data.stateId, "countryId": data.countryId, "pinCode": data.pinCode,
        "phone": data.phoneNumber, "isDefault": data.isDefault or False,
        "userProfileId": user_profile_id, "typeId": data.typeId,
        "createdDate": datetime.now(timezone.utc), "deletedInd": False,
        "isBillingAddress": data.isBillingAddress
    }
    result = db.execute(text("""
        INSERT INTO twam."Address"
        ("Name","AddressLine","Locality","City","StateId","CountryId","PinCode","Phone",
         "IsDefault","UserProfileId","TypeId","CreatedDate","DeletedInd","IsBillingAddress")
        VALUES (:name,:addressLine,:locality,:city,:stateId,:countryId,:pinCode,:phone,
                :isDefault,:userProfileId,:typeId,:createdDate,:deletedInd,:isBillingAddress)
        RETURNING "AddressId"
    """), address)
    address_id = result.fetchone()[0]
    db.commit()

    if data.shippingTypeId and data.deliveryCharge is None:
        delivery_info = _get_delivery_info(db, data.shippingTypeId)
        if delivery_info and delivery_info.get("deliveryCharges") is not None:
            data.deliveryCharge = delivery_info["deliveryCharges"]

    order = Orders(
        orderNumber=generate_order_number(),
        totalAmount=data.totalAmount,
        orderDate=getattr(data, "orderDate", None) or datetime.now(timezone.utc),
        userProfileId=user_profile_id,
        state="Pending",
        createdDate=datetime.now(timezone.utc),
        deletedInd=False,
        shippingAddressId=address_id,
        billingAddressId=address_id,
        personalId=0,
        couponId=data.couponId,
        shippingTypeId=data.shippingTypeId,
        couponAmount=data.couponAmount,
        deliveryCharge=data.deliveryCharge,
        taxAmount=data.taxAmount,
        subTotal=data.subTotal,
        isWhatsappNotification=data.isWhatsappNotification,
    )
    db.add(order)
    db.flush()
    order_id = order.orderId

    pvd_map = {}
    if order_items_input:
        pvd_ids = [i.productVariantDetailId for i in order_items_input if i.productVariantDetailId]
        if pvd_ids:
            ids_str = ",".join(str(i) for i in pvd_ids)
            rows = db.execute(text(
                f'SELECT "ProductVariantDetailId","CGST","SGST","TaxAmount","FinalPrice" FROM twam."ProductVariantDetail" WHERE "ProductVariantDetailId" IN ({ids_str})'
            )).fetchall()
            pvd_map = {r[0]: {"cgst": r[1], "sgst": r[2], "taxAmount": r[3], "finalPrice": r[4]} for r in rows}

        total_tax = 0
        for x in order_items_input:
            variant     = pvd_map.get(x.productVariantDetailId, {})
            tax         = float(variant.get("taxAmount") or 0)
            final_price = float(variant.get("finalPrice") or 0)
            total_tax  += tax

            # ── BUG FIX: use PascalCase attribute names ──────────────────────
            db.add(OrderItems(
                OrderId                = order_id,
                OrderItemNumber        = generate_order_item_number(),
                ProductVariantDetailId = x.productVariantDetailId,
                ProductVariantId       = x.productVariantId,
                ProductId              = x.productId,
                Quantity               = x.quantity,
                Price                  = x.price,
                CreatedDate            = datetime.now(timezone.utc),
                DeletedInd             = False,
                TaxAmount              = tax,
                CGST                   = variant.get("cgst"),
                SGST                   = variant.get("sgst"),
                UnitPrice              = final_price - tax if final_price else None,
            ))
        order.taxAmount = total_tax

    db.commit()

    # TODO: Integrate IPaymentService.CreateOrderRequestAsync
    return {"orderId": order_id, "paymentProcessUrl": None}


# ── Cancel Order ──────────────────────────────────────────────────────────────

def cancel_order(db: Session, order_id: int, is_refund: bool, reason: str, platform: str) -> bool:
    order = db.query(Orders).filter(
        Orders.orderId == order_id, Orders.deletedInd == False
    ).first()
    if not order:
        raise ValueError("Order not found.")

    new_state = "Refunded" if is_refund else "Cancelled"
    order.state    = new_state
    order.reason   = reason
    order.platform = platform
    order.modifiedDate = datetime.now(timezone.utc)

    db.add(OrderTrackingStatus(
        orderId=order_id,
        status=new_state,
        createdDate=datetime.now(timezone.utc)
    ))

    # Revert stock via stored procedure
    try:
        db.execute(
            text("CALL twam.RevertStockQuantity(:order_id, :is_revert)"),
            {"order_id": order_id, "is_revert": "1"}
        )
    except Exception:
        pass

    # TODO: Integrate IPaymentService.RefundPaymentAsync
    db.commit()
    
    # Send cancellation notification
    try:
        from app.ekart.notifications import send_order_cancelled_notification
        send_order_cancelled_notification(db, order_id, reason)
    except Exception as e:
        print(f"[Order] Cancel notification failed for order {order_id}: {e}")
    
    return True


# ── Return Order ──────────────────────────────────────────────────────────────

def create_return_order(db: Session, data) -> bool:
    try:
        return_order = Orders(
            orderNumber=generate_order_number(),
            referenceOrderId=data.orderId,
            deletedInd=False,
            isReturn=True,
            state="Return Initiated",
            createdDate=datetime.now(timezone.utc),
            personalId=0
        )
        db.add(return_order)
        db.flush()
        order_id = return_order.orderId

        db.add(OrderTrackingStatus(
            orderId=order_id,
            status="Return Initiated",
            createdDate=datetime.now(timezone.utc)
        ))

        for x in (data.orderItems or []):
            # ── BUG FIX: use PascalCase attribute names ──────────────────────
            db.add(OrderItems(
                OrderId              = order_id,
                OrderItemNumber      = generate_order_item_number(),
                Quantity             = x.quantity,
                Price                = x.price,
                ReferenceOrderItemId = x.orderItemId,
                IsReturn             = True,
                CreatedDate          = datetime.now(timezone.utc),
                DeletedInd           = False,
            ))

        db.add(OrderReturnInfo(
            orderId=order_id,
            reasonId=data.reasonId,
            reason=data.reason,
            otherReason=data.otherReason,
            refundChoice=data.shippingOption,
            createdDate=datetime.now(timezone.utc),
            deletedInd=False,
        ))

        db.commit()
        
        # Send return initiated notification
        try:
            from app.ekart.notifications import send_return_initiated_notification
            send_return_initiated_notification(db, data.orderId)  # Notify for original order
        except Exception as e:
            print(f"[Order] Return notification failed for order {order_id}: {e}")
        
        return True
    except Exception:
        db.rollback()
        return False


# ── Get Order List ────────────────────────────────────────────────────────────

def get_order_list(db: Session, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(Orders).filter(Orders.deletedInd == False)

    days_value, remaining_filters = None, []
    if filters:
        for f in filters:
            if f.get("property") == "days":
                days_value = f.get("value")
            else:
                remaining_filters.append(f)

    from datetime import timedelta
    now = datetime.now()
    if days_value == "30":
        query = query.filter(Orders.orderDate >= now - timedelta(days=30))
    elif days_value == "180":
        query = query.filter(Orders.orderDate >= now - timedelta(days=180))
    elif days_value in ("1", "-1"):
        query = query.filter(Orders.orderDate != None)

    query = apply_filters(query, Orders, remaining_filters)
    query = apply_ordering(query, Orders, order_property, order_ascending)
    total = query.count()
    query = apply_pagination(query, page_index, page_size)
    orders = query.all()

    order_ids = [o.orderId for o in orders]
    items_map = {}
    for item in _get_order_items_with_details(db, order_ids, include_reviews=True):
        items_map.setdefault(item["orderId"], []).append(item)

    result = []
    for o in orders:
        result.append({
            "orderId": o.orderId,
            "totalAmount": float(o.totalAmount) if o.totalAmount else None,
            "orderDate": o.orderDate,
            "userProfileId": o.userProfileId,
            "state": o.state,
            "orderNumber": o.orderNumber,
            "shippingAddressId": o.shippingAddressId,
            "paymentAccount": o.paymentAccount,
            "paymentTransactionRefNo": o.paymentTransactionRefNo,
            "couponAmount": float(o.couponAmount) if o.couponAmount else None,
            "deliveryCharge": float(o.deliveryCharge) if o.deliveryCharge else None,
            "taxAmount": float(o.taxAmount) if o.taxAmount else None,
            "subTotal": float(o.subTotal) if o.subTotal else None,
            "isShipped": o.isShipped,
            "reason": o.reason,
            "deliveredDate": o.deliveredDate,
            "address": _get_address(db, o.shippingAddressId),
            "deliveryInfo": _get_delivery_info(db, o.shippingTypeId),
            "orderItems": items_map.get(o.orderId, []),
        })

    return build_paged_response(total, result)


# ── Get Admin Order List ──────────────────────────────────────────────────────

def get_admin_order_list(db: Session, filters, order_ascending, order_property,
                         page_index, page_size, start_date=None, end_date=None) -> dict:
    query = db.query(Orders).filter(Orders.deletedInd == False)

    if start_date and end_date:
        sd = datetime.fromisoformat(start_date)
        ed = datetime.fromisoformat(end_date)
        query = query.filter(Orders.orderDate >= sd, Orders.orderDate <= ed)

    query = apply_filters(query, Orders, filters)
    query = apply_ordering(query, Orders, order_property, order_ascending)
    total = query.count()
    query = apply_pagination(query, page_index, page_size)
    orders = query.all()

    ref_ids = [o.referenceOrderId for o in orders if o.referenceOrderId]
    ref_agent_map = {}
    if ref_ids:
        ref_orders = db.query(Orders).filter(Orders.orderId.in_(ref_ids)).all()
        ref_agent_map = {o.orderId: o.deliveryAgent for o in ref_orders}

    order_ids = [o.orderId for o in orders]
    items_map = {}
    for item in _get_order_items_with_details(db, order_ids):
        items_map.setdefault(item["orderId"], []).append(item)

    result = []
    for o in orders:
        order_items = items_map.get(o.orderId, [])
        total_items = len(order_items)
        total_qty   = sum(i.get("quantity") or 0 for i in order_items)
        for item in order_items:
            item["totalItems"]    = total_items
            item["totalQuantity"] = total_qty

        result.append({
            "orderId": o.orderId,
            "totalAmount": float(o.totalAmount) if o.totalAmount else None,
            "orderDate": o.orderDate,
            "userProfileId": o.userProfileId,
            "state": o.state,
            "orderNumber": o.orderNumber,
            "shippingAddressId": o.shippingAddressId,
            "paymentAccount": o.paymentAccount,
            "paymentTransactionRefNo": o.paymentTransactionRefNo,
            "couponAmount": float(o.couponAmount) if o.couponAmount else None,
            "deliveryCharge": float(o.deliveryCharge) if o.deliveryCharge else None,
            "taxAmount": float(o.taxAmount) if o.taxAmount else None,
            "subTotal": float(o.subTotal) if o.subTotal else None,
            "reason": o.reason,
            "deliveryAgent": o.deliveryAgent or ref_agent_map.get(o.referenceOrderId),
            "referenceOrderId": o.referenceOrderId,
            "address": _get_address(db, o.shippingAddressId),
            "orderItems": order_items,
        })

    return build_paged_response(total, result)


# ── Get Order Details ─────────────────────────────────────────────────────────

def get_order_details(db: Session, order_id: int) -> Optional[dict]:
    order = db.query(Orders).filter(
        Orders.orderId == order_id, Orders.deletedInd == False
    ).first()
    if not order:
        return None

    items = _get_order_items_with_details(db, [order_id])

    return {
        "orderId": order.orderId,
        "totalAmount": float(order.totalAmount) if order.totalAmount else None,
        "orderDate": order.orderDate,
        "userProfileId": order.userProfileId,
        "state": order.state,
        "orderNumber": order.orderNumber,
        "shippingAddressId": order.shippingAddressId,
        "billingAddressId": order.billingAddressId,
        "paymentAccount": order.paymentAccount,
        "paymentTransactionRefNo": order.paymentTransactionRefNo,
        "paymentStatus": None,
        "paymentReasonCode": None,
        "subTotal": float(order.subTotal) if order.subTotal else None,
        "taxAmount": float(order.taxAmount) if order.taxAmount else None,
        "deliveryCharge": float(order.deliveryCharge) if order.deliveryCharge else None,
        "shippingAddress": _get_address(db, order.shippingAddressId),
        "billingAddress": _get_address(db, order.billingAddressId),
        "deliveryInfo": _get_delivery_info(db, order.shippingTypeId),
        "orderItems": items,
    }


# ── Order Tracking ────────────────────────────────────────────────────────────

def get_order_tracking(db: Session, order_id: int) -> dict:
    order = db.query(Orders).filter(Orders.orderId == order_id).first()
    if not order:
        return {"steps": [{"title": "Error", "description": "Order not found.", "status": "pending"}]}

    statuses   = db.query(OrderTrackingStatus).filter(OrderTrackingStatus.orderId == order_id).all()
    status_map = {s.status: s for s in statuses}

    def _fmt(key):
        s = status_map.get(key)
        return s.createdDate.strftime("%Y-%m-%d %H:%M:%S") if s and s.createdDate else None

    steps = []
    if "Pending"          in status_map:
        steps.append({"title": "Order Pending",   "description": "Awaiting payment confirmation", "date": _fmt("Pending"),          "status": "done"})
    if "Failed"           in status_map:
        steps.append({"title": "Order Failed",    "description": f"Order {order.orderNumber} failed.", "date": _fmt("Failed"),      "status": "done"})
    if "Confirmed"        in status_map:
        steps.append({"title": "Order Confirmed", "description": "Your order has been placed.",  "date": _fmt("Confirmed"),         "status": "done"})

    # Shipped / in-transit / delivered — derived from Orders table directly
    if order.isShipped and order.state not in ("Cancelled", "Returned"):
        tracking_note = f"Tracking ID: {order.trackingId}" if order.trackingId else "Your order is on its way."
        if order.state == "Delivered":
            steps.append({
                "title": "Shipped",
                "description": tracking_note,
                "date": None,
                "status": "done"
            })
            delivered_date = (
                order.deliveredDate.strftime("%Y-%m-%d %H:%M:%S")
                if order.deliveredDate else None
            )
            steps.append({
                "title": "Delivered",
                "description": "Your order has been delivered.",
                "date": delivered_date,
                "status": "done"
            })
        else:
            steps.append({
                "title": "Shipped",
                "description": tracking_note,
                "date": None,
                "status": "done"
            })
            steps.append({
                "title": "Out for delivery",
                "description": "Your order is on its way.",
                "date": None,
                "status": "active"
            })

    if "Return Initiated" in status_map:
        steps.append({"title": "Return Initiated","description": "Order return initiated.",      "date": _fmt("Return Initiated"),  "status": "done"})
    if order.state == "Cancelled":
        steps.append({"title": "Order Cancelled", "description": "Order was cancelled.",         "date": _fmt("Cancelled"),         "status": "done"})
    if order.state == "Returned":
        steps.append({"title": "Order Returned",  "description": "Order returned and refunded.", "date": _fmt("Returned"),          "status": "done"})

    refund = db.query(OrderRefund).filter(OrderRefund.orderId == order_id).first()
    if refund and refund.refundDateTime:
        steps.append({"title": "Refund Initiated", "description": "Refund initiated.",
                      "date": refund.refundDateTime.strftime("%Y-%m-%d %H:%M:%S"), "status": "done"})
        if refund.refundPaymentResponseCode in (0, 1):
            steps.append({
                "title": "Refunded",
                "description": f"{order.totalAmount} refunded to your original payment method.",
                "date": refund.updatedDateTime.strftime("%Y-%m-%d %H:%M:%S") if refund.updatedDateTime else None,
                "status": "done"
            })

    return {"steps": steps}


# ── Return Order Items ────────────────────────────────────────────────────────

def get_return_order_items(db: Session, order_id: int, filters, order_ascending,
                           order_property, page_index, page_size) -> dict:
    order = db.query(Orders).filter(
        Orders.orderId == order_id, Orders.deletedInd == False
    ).first()
    if not order:
        return None

    from datetime import timedelta
    return_expiry = (order.orderDate + timedelta(days=7)) if order.orderDate else None
    now = datetime.now(timezone.utc)

    sql = f"""
        SELECT
            oi."OrderItemId", oi."Quantity", oi."Price",
            p."Name", s."SizeLabel", pv."Color", pv."IsReturnAvailable",
            (SELECT CONCAT('{BASE_URL}', pi2."FilePath")
             FROM twam."ProductImage" pi2
             WHERE pi2."ProductVariantId" = oi."ProductVariantId" AND pi2."DeletedInd" = false
             LIMIT 1) AS product_image
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products" p ON p."ProductId" = oi."ProductId"
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = oi."ProductVariantId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
        LEFT JOIN mdm."Size" s ON s."SizeId" = pvd."Size"
        WHERE oi."OrderId" = :order_id AND oi."DeletedInd" = false AND pv."IsReturnAvailable" = true
    """
    rows = db.execute(text(sql), {"order_id": order_id}).fetchall()

    items = [{
        "orderItemId": r[0], "quantity": r[1],
        "price": float(r[2]) if r[2] else None,
        "productName": r[3], "size": r[4], "color": r[5],
        "isReturnable": r[6] or False,
        "productImage": r[7] or "",
        "returnExpiryDate": return_expiry,
        "isReturnExpired": (now > return_expiry) if return_expiry else None,
    } for r in rows]

    return {
        "count": 1,
        "list": [{
            "orderId": order.orderId,
            "orderNumber": order.orderNumber,
            "orderDate": order.deliveredDate or order.orderDate,
            "orderItems": items
        }],
        "parameters": None
    }


# ── Update Order Status (Admin) ───────────────────────────────────────────────

def update_order_status(
    db: Session, 
    order_id: int, 
    new_state: str,
    tracking_id: str = None,
    delivery_agent: str = None,
) -> bool:
    """
    Update order status and send appropriate notifications.
    Used by admin panel and Ekart webhooks.
    """
    order = db.query(Orders).filter(
        Orders.orderId == order_id,
        Orders.deletedInd == False
    ).first()
    
    if not order:
        return False
    
    old_state = order.state
    order.state = new_state
    order.modifiedDate = datetime.now(timezone.utc)
    
    # Update tracking info if provided
    if tracking_id:
        order.trackingId = tracking_id
        order.isShipped = True
    
    if delivery_agent:
        order.deliveryAgent = delivery_agent
    
    # Set delivered date
    if new_state == "Delivered" and not order.deliveredDate:
        order.deliveredDate = datetime.now(timezone.utc)
    
    # Add tracking status record
    db.add(OrderTrackingStatus(
        orderId=order_id,
        status=new_state,
        createdDate=datetime.now(timezone.utc)
    ))
    
    db.commit()
    
    # Send notifications based on state change
    if old_state != new_state:
        try:
            from app.ekart.notifications import send_order_status_notification
            import asyncio
            
            # Run async notification in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(send_order_status_notification(db, order_id, new_state))
            finally:
                loop.close()
        except Exception as e:
            print(f"[Order] Status notification failed for order {order_id}: {e}")
    
    return True
