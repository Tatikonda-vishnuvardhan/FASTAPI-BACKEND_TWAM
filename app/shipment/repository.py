"""
app/shipment/repository.py  (UPDATED)
──────────────────────────────────────
Key changes:
  ① _build_return_address() now reads from DB (ShipmentConfigurations)
    — no more os.getenv() for warehouse address.
  ② All Ekart client calls use get_ekart_client_for_db(db) — DB credentials.
  ③ Minor: _create_ekart_forward_shipment / _create_ekart_return_shipment
    pass db to client factory.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from .models import Shipment
from app.ekart.client import get_ekart_client_for_db
from app.ekart.schemas import (
    CreateReturnShipmentRequest as EkartCreateReturnShipmentRequest,
    CreateShipmentRequest as EkartCreateShipmentRequest,
    EkartAddress,
    EkartShipmentItem,
)

BASE_URL = os.getenv("BASE_URL", "")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_order(db: Session, order_id: int) -> Optional[dict]:
    row = db.execute(
        text("""
            SELECT "OrderId","OrderNumber","ShippingAddressId","UserProfileId",
                   "TotalAmount","TaxAmount","OrderDate","ReferenceOrderId"
            FROM twam."Orders" WHERE "OrderId"=:id AND "DeletedInd"=false LIMIT 1
        """),
        {"id": order_id}
    ).fetchone()
    if not row:
        return None
    return {
        "orderId": row[0], "orderNumber": row[1], "shippingAddressId": row[2],
        "userProfileId": row[3], "totalAmount": row[4], "taxAmount": row[5],
        "orderDate": row[6], "referenceOrderId": row[7],
    }


def _get_address_with_state_country(db: Session, address_id: int) -> Optional[dict]:
    row = db.execute(
        text("""
            SELECT a."AddressLine", a."City", a."PinCode", a."Phone", a."Name",
                   s."StateName", c."CountryName"
            FROM twam."Address" a
            LEFT JOIN mdm."State"   s ON s."StateId"   = a."StateId"
            LEFT JOIN mdm."Country" c ON c."CountryId" = a."CountryId"
            WHERE a."AddressId"=:id AND a."DeletedInd"=false LIMIT 1
        """),
        {"id": address_id}
    ).fetchone()
    if not row:
        return None
    return {
        "addressLine": row[0], "city": row[1], "pinCode": row[2],
        "phone": row[3], "name": row[4], "stateName": row[5], "countryName": row[6],
    }


def _get_invoice(db: Session, order_id: int) -> Optional[dict]:
    try:
        row = db.execute(
            text('SELECT "InvoiceNumber","CreatedDate" FROM twam."Invoice" WHERE "OrderId"=:id LIMIT 1'),
            {"id": order_id}
        ).fetchone()
        return {"invoiceNumber": row[0], "createdDate": row[1]} if row else None
    except Exception:
        return None


def _get_user_full_name(db: Session, user_profile_id: str) -> str:
    try:
        row = db.execute(
            text('SELECT "FirstName","MiddleName","LastName" FROM twam."People" WHERE "UserProfileId"=:uid LIMIT 1'),
            {"uid": user_profile_id}
        ).fetchone()
        if row:
            return " ".join(part for part in [row[0], row[1], row[2]] if part and part.strip())
        return ""
    except Exception:
        return ""


def _get_hsn_codes_for_order(db: Session, order_id: int) -> str:
    try:
        rows = db.execute(text("""
            SELECT DISTINCT h."HSNCode"
            FROM twam."OrderItems" oi
            JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = oi."ProductVariantId"
            JOIN twam."TaxHSNCode" h ON h."TaxHSNCodeId" = pv."TaxHSNCodeId"
            WHERE oi."OrderId" = :oid AND oi."DeletedInd" = false AND h."HSNCode" IS NOT NULL
        """), {"oid": order_id}).fetchall()
        return ",".join(r[0] for r in rows if r[0])
    except Exception:
        return ""


def _get_order_item_count(db: Session, order_id: int) -> int:
    row = db.execute(
        text('SELECT COALESCE(SUM("Quantity"),0) FROM twam."OrderItems" WHERE "OrderId"=:oid AND "DeletedInd"=false'),
        {"oid": order_id}
    ).fetchone()
    return int(row[0]) if row else 0


def _number_to_words(amount) -> str:
    return str(amount)


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _get_order_items_for_ekart(db: Session, order_id: int) -> list[EkartShipmentItem]:
    rows = db.execute(text("""
        SELECT
            p."Name",
            COALESCE(pv."SKU", p."SKU"),
            oi."Quantity",
            oi."Price",
            thc."HSNCode"
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products" p ON p."ProductId" = oi."ProductId"
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = oi."ProductVariantId"
        LEFT JOIN twam."TaxHSNCode" thc ON thc."TaxHSNCodeId" = COALESCE(pv."TaxHSNCodeId", p."TaxHSNCodeId")
        WHERE oi."OrderId" = :order_id AND oi."DeletedInd" = false
    """), {"order_id": order_id}).fetchall()

    return [
        EkartShipmentItem(
            name=row[0] or "Product",
            sku=row[1],
            quantity=int(row[2] or 1),
            price=float(row[3]) if row[3] is not None else 0.0,
            hsn_code=row[4],
        )
        for row in rows
    ]


def _build_return_address_from_db(db: Session) -> EkartAddress:
    """
    Load warehouse return address from shipment.ShipmentConfigurations.
    Falls back to sensible defaults with clear [FILL] markers so the
    admin knows what to configure.
    """
    try:
        from app.shipment.config_model import ShipmentConfigurations
        row = (
            db.query(ShipmentConfigurations)
            .filter(
                ShipmentConfigurations.deliveryAgent.ilike("EKart%"),
                ShipmentConfigurations.deletedInd == False,
                ShipmentConfigurations.stateId == "Active",
            )
            .first()
        )
        if row and row.returnAddressLine1:
            return EkartAddress(
                name=         row.returnName         or "Only TWAM Warehouse",
                phone=        row.returnPhone         or "",
                address_line1=row.returnAddressLine1  or "",
                address_line2=row.returnAddressLine2  or None,
                city=         row.returnCity          or "",
                state=        row.returnState         or "",
                pincode=      row.returnPinCode       or "",
                country=      row.returnCountry       or "India",
            )
    except Exception as e:
        print(f"[Shipment] Could not load return address from DB: {e}")

    # Fallback — admin should fill these in ShipmentConfigurations table
    return EkartAddress(
        name="Only TWAM Warehouse",
        phone="",
        address_line1="[FILL: Update ReturnAddressLine1 in ShipmentConfigurations]",
        city="",
        state="",
        pincode="",
        country="India",
    )


# ── Ekart API call helpers ────────────────────────────────────────────────────

def _create_ekart_forward_shipment(db: Session, data, order: dict) -> tuple[Optional[str], Optional[str]]:
    manual_tracking_id = getattr(data, "manualTrackingId", None) or None
    if manual_tracking_id:
        return manual_tracking_id, None

    address = _get_address_with_state_country(db, order["shippingAddressId"]) if order.get("shippingAddressId") else None
    if not address:
        return None, "Shipping address not found for this order."

    items = _get_order_items_for_ekart(db, order["orderId"])
    if not items:
        return None, "Order has no items to create a shipment."

    request = EkartCreateShipmentRequest(
        order_id=order["orderId"],
        order_number=order.get("orderNumber") or str(order["orderId"]),
        invoice_number=getattr(data, "invoiceNumber", None),
        invoice_date=getattr(data, "invoiceDate", None),
        consignee_name=getattr(data, "consigneeName", None) or address.get("name") or "Customer",
        consignee_phone=address.get("phone") or "",
        consignee_address=EkartAddress(
            name=address.get("name") or "Customer",
            phone=address.get("phone") or "",
            address_line1=address.get("addressLine") or "",
            city=address.get("city") or "",
            state=address.get("stateName") or "",
            pincode=address.get("pinCode") or "",
            country=address.get("countryName") or "India",
        ),
        payment_mode=(getattr(data, "paymentMode", None) or "PREPAID").upper(),
        cod_amount=getattr(data, "codAmount", None),
        total_amount=float(getattr(data, "totalAmount", None) or order.get("totalAmount") or 0),
        weight=float(getattr(data, "weight", None) or 0.5),
        length=getattr(data, "length", None) or 20,
        width=getattr(data, "width", None) or 15,
        height=getattr(data, "height", None) or 10,
        items=items,
        product_description=getattr(data, "productDescription", None),
        tax_value=getattr(data, "taxValue", None),
        taxable_amount=getattr(data, "taxableAmount", None),
    )

    # ← Use DB-configured client
    result = _run_async(get_ekart_client_for_db(db).create_shipment(request))
    if not result.success:
        return None, result.error_message or "Failed to create shipment in Ekart."
    return result.awb_number, None


def _create_ekart_return_shipment(db: Session, data, order: dict) -> tuple[Optional[str], Optional[str]]:
    manual_tracking_id = getattr(data, "manualTrackingId", None) or None
    if manual_tracking_id:
        return manual_tracking_id, None

    address = _get_address_with_state_country(db, order["shippingAddressId"]) if order.get("shippingAddressId") else None
    if not address:
        return None, "Pickup address not found for this return order."

    items = _get_order_items_for_ekart(db, order["orderId"])
    if not items:
        return None, "Return order has no items to create a pickup."

    request = EkartCreateReturnShipmentRequest(
        order_id=order["orderId"],
        original_awb="",
        return_reason=getattr(data, "returnReason", None) or "Customer return",
        pickup_name=address.get("name") or "Customer",
        pickup_phone=address.get("phone") or "",
        pickup_address=EkartAddress(
            name=address.get("name") or "Customer",
            phone=address.get("phone") or "",
            address_line1=address.get("addressLine") or "",
            city=address.get("city") or "",
            state=address.get("stateName") or "",
            pincode=address.get("pinCode") or "",
            country=address.get("countryName") or "India",
        ),
        return_address=_build_return_address_from_db(db),  # ← DB-sourced
        weight=float(getattr(data, "weight", None) or 0.5),
        items=items,
    )

    result = _run_async(get_ekart_client_for_db(db).create_return_shipment(request))
    if not result.success:
        return None, result.error_message or "Failed to create return shipment in Ekart."
    return result.awb_number, None


def _persist_shipment(db: Session, data, order: dict, tracking_id: str) -> int:
    ship = Shipment(
        orderId             = data.get("orderId"),
        sellerId            = data.get("sellerId"),
        consigneeGSTAmount  = data.get("consigneeGSTAmount"),
        orderNumber         = data.get("orderNumber"),
        invoiceNumber       = data.get("invoiceNumber"),
        invoiceDate         = data.get("invoiceDate"),
        consigneeName       = data.get("consigneeName"),
        productDescription  = data.get("productDescription"),
        paymentMode         = data.get("paymentMode"),
        goodsCategory       = data.get("goodsCategory"),
        totalAmount         = data.get("totalAmount"),
        taxValue            = data.get("taxValue"),
        taxableAmount       = data.get("taxableAmount"),
        commodityValue      = data.get("commodityValue"),
        codAmount           = data.get("codAmount"),
        quantity            = data.get("quantity"),
        weight              = data.get("weight"),
        length              = data.get("length"),
        height              = data.get("height"),
        width               = data.get("width"),
        pickupAddressId     = data.get("pickupAddressId"),
        dropAddressId       = order.get("shippingAddressId"),
        returnAddressId     = data.get("returnAddressId") or data.get("pickupAddressId"),
        isSameReturnAddress = data.get("isSameReturnAddress"),
        trackingId          = tracking_id,
        createdDate         = datetime.now(timezone.utc),
        deletedInd          = False,
    )
    db.add(ship)
    db.flush()
    db.commit()
    return ship.shipmentId


def _update_order_and_items(db: Session, order_id: int, tracking_id: str, agent: str):
    db.execute(text("""
        UPDATE twam."Orders"
        SET "TrackingId"=:tid, "IsShipped"=true, "DeliveryAgent"=:agent, "State"='Processing',
            "ModifiedDate"=NOW()
        WHERE "OrderId"=:oid
    """), {"tid": tracking_id, "agent": agent, "oid": order_id})
    db.execute(text("""
        UPDATE twam."OrderItems" SET "TrackingId"=:tid WHERE "OrderId"=:oid
    """), {"tid": tracking_id, "oid": order_id})
    db.commit()


# ── Create Ekart Forward Shipment ─────────────────────────────────────────────

def create_shipment(db: Session, data) -> dict:
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    tracking_id, error_message = _create_ekart_forward_shipment(db, data, order)
    if not tracking_id:
        return {
            "trackingId": None,
            "success": False,
            "message": error_message or "No tracking ID available from Ekart.",
        }

    ship_data = {
        "orderId": data.orderId, "sellerId": data.sellerId,
        "consigneeGSTAmount": data.consigneeGSTAmount, "orderNumber": data.orderNumber,
        "invoiceNumber": data.invoiceNumber, "invoiceDate": data.invoiceDate,
        "consigneeName": data.consigneeName, "productDescription": data.productDescription,
        "paymentMode": data.paymentMode, "goodsCategory": data.goodsCategory,
        "totalAmount": data.totalAmount, "taxValue": data.taxValue,
        "taxableAmount": data.taxableAmount, "commodityValue": data.commodityValue,
        "codAmount": data.codAmount, "quantity": data.quantity, "weight": data.weight,
        "length": data.length, "height": data.height, "width": data.width,
        "pickupAddressId": data.pickupAddressId, "returnAddressId": data.returnAddressId,
        "isSameReturnAddress": data.isSameReturnAddress,
    }
    _persist_shipment(db, ship_data, order, tracking_id)
    _update_order_and_items(db, data.orderId, tracking_id, "EKart")

    # Add tracking status
    from app.orders.models import OrderTrackingStatus
    db.add(OrderTrackingStatus(
        orderId=data.orderId,
        status="Processing",
        createdDate=datetime.now(timezone.utc),
    ))
    db.commit()

    # Notify customer — shipment created
    try:
        from app.ekart.notifications import send_order_shipped_notification
        _run_async(send_order_shipped_notification(db, data.orderId))
    except Exception as e:
        print(f"[Shipment] Notification failed: {e}")

    return {"trackingId": tracking_id, "success": True, "message": "Shipment created."}


# ── Create Ekart Return Shipment ──────────────────────────────────────────────

def create_return_shipment(db: Session, data) -> int:
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    tracking_id, _ = _create_ekart_return_shipment(db, data, order)

    if tracking_id:
        ship_data = {
            "orderId": data.orderId, "sellerId": data.sellerId,
            "consigneeGSTAmount": data.consigneeGSTAmount, "orderNumber": data.orderNumber,
            "invoiceNumber": data.invoiceNumber, "invoiceDate": data.invoiceDate,
            "consigneeName": data.consigneeName, "productDescription": data.productDescription,
            "paymentMode": data.paymentMode, "goodsCategory": data.goodsCategory,
            "totalAmount": data.totalAmount, "taxValue": data.taxValue,
            "taxableAmount": data.taxableAmount, "commodityValue": data.commodityValue,
            "codAmount": data.codAmount, "quantity": data.quantity, "weight": data.weight,
            "length": data.length, "height": data.height, "width": data.width,
            "pickupAddressId": data.pickupAddressId, "returnAddressId": data.returnAddressId,
            "isSameReturnAddress": data.isSameReturnAddress,
        }
        _persist_shipment(db, ship_data, order, tracking_id)
        _update_order_and_items(db, data.orderId, tracking_id, "EKart")
        return 1
    return 0


# ── Create Delhivery Shipment ─────────────────────────────────────────────────

def create_delhivery_shipment(db: Session, data) -> int:
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    tracking_id = getattr(data, "manualTrackingId", None) or None

    if tracking_id:
        ship_data = {
            "orderId": data.orderId, "sellerId": data.sellerId,
            "consigneeGSTAmount": 0, "orderNumber": data.orderNumber,
            "invoiceNumber": data.invoiceNumber, "invoiceDate": None,
            "consigneeName": data.consigneeName, "productDescription": data.productDescription,
            "paymentMode": data.paymentMode, "goodsCategory": None,
            "totalAmount": data.totalAmount, "taxValue": None, "taxableAmount": None,
            "commodityValue": None, "codAmount": data.codAmount, "quantity": data.quantity,
            "weight": data.weight, "pickupAddressId": data.pickupAddressId,
            "isSameReturnAddress": data.isSameReturnAddress,
        }
        _persist_shipment(db, ship_data, order, tracking_id)
        _update_order_and_items(db, data.orderId, tracking_id, "Delhivery")
    return 1


# ── Cancel Shipment ───────────────────────────────────────────────────────────

def cancel_shipment(db: Session, order_id: int) -> bool:
    ship = db.query(Shipment).filter(
        Shipment.orderId == order_id,
        Shipment.deletedInd == False
    ).first()
    if not ship:
        raise ValueError("Shipment not found.")

    # Try to cancel on Ekart first
    if ship.trackingId:
        from app.ekart.schemas import CancelShipmentRequest
        try:
            result = _run_async(
                get_ekart_client_for_db(db).cancel_shipment(
                    CancelShipmentRequest(
                        awb_number=ship.trackingId,
                        reason="Cancelled by admin"
                    )
                )
            )
            if not result.success:
                print(f"[Shipment] Ekart cancel failed: {result.error_message}")
        except Exception as e:
            print(f"[Shipment] Ekart cancel error: {e}")

    ship.deletedInd   = True
    ship.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Track Shipment (live from Ekart) ─────────────────────────────────────────

def track_shipment_live(db: Session, tracking_id: str) -> dict:
    """
    Fetch live tracking from Ekart Elite API and merge with DB state.
    Returns combined tracking info.
    """
    # DB state
    row = db.execute(
        text("""
            SELECT s."TrackingId", s."OrderNumber", s."State",
                   s."ConsigneeName", s."CreatedDate",
                   o."State" AS order_state, o."DeliveredDate", o."IsShipped",
                   o."OrderId"
            FROM shipment."Shipment" s
            LEFT JOIN twam."Orders" o ON o."TrackingId" = s."TrackingId"
            WHERE s."TrackingId" = :tid AND s."DeletedInd" = false
            LIMIT 1
        """),
        {"tid": tracking_id}
    ).fetchone()

    db_info = None
    if row:
        db_info = {
            "trackingId":   row[0],
            "orderNumber":  row[1],
            "shipmentState": row[2],
            "consigneeName": row[3],
            "createdDate":  row[4].isoformat() if row[4] else None,
            "orderState":   row[5],
            "deliveredDate": row[6].isoformat() if row[6] else None,
            "isShipped":    row[7],
            "orderId":      row[8],
        }

    # Live from Ekart
    try:
        ekart_result = _run_async(
            get_ekart_client_for_db(db).track_shipment(tracking_id)
        )
        live_events = [
            {
                "status":    e.status,
                "location":  e.location,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "remarks":   e.remarks,
            }
            for e in ekart_result.events
        ]
        live_status = ekart_result.current_status
        estimated_delivery = ekart_result.expected_delivery.isoformat() if ekart_result.expected_delivery else None
    except Exception as e:
        print(f"[Shipment] Live tracking fetch failed: {e}")
        live_events = []
        live_status = None
        estimated_delivery = None

    return {
        **(db_info or {"trackingId": tracking_id}),
        "liveStatus":         live_status,
        "estimatedDelivery":  estimated_delivery,
        "trackingEvents":     live_events,
    }


# ── GetShipmentDataQuery ──────────────────────────────────────────────────────

def get_shipment_data(db: Session, order_id: int) -> dict:
    order = _get_order(db, order_id)
    if not order:
        raise ValueError("Order not found.")

    invoice   = _get_invoice(db, order_id)
    full_name = _get_user_full_name(db, order["userProfileId"] or "")
    total_qty = _get_order_item_count(db, order_id)
    total     = float(order["totalAmount"] or 0)
    tax       = float(order["taxAmount"] or 0)

    return {
        "consigneeName":     full_name,
        "orderNumber":       order["orderNumber"],
        "invoiceNumber":     invoice["invoiceNumber"] if invoice else "",
        "invoiceDate":       invoice["createdDate"]   if invoice else datetime.now(timezone.utc),
        "totalAmount":       total,
        "taxableAmount":     tax,
        "taxValue":          total - tax,
        "consigneeGSTAmount": tax,
        "quantity":          total_qty,
        "commodityValue":    _number_to_words(tax),
        "productDescription": None,
        "paymentMode":       None,
        "goodsCategory":     None,
        "weight":            None,
        "codAmount":         None,
    }


def get_delhivery_shipment_data(db: Session, order_id: int) -> dict:
    order = _get_order(db, order_id)
    if not order:
        raise ValueError("Order not found.")

    invoice   = _get_invoice(db, order_id)
    full_name = _get_user_full_name(db, order["userProfileId"] or "")
    drop_addr = _get_address_with_state_country(db, order["shippingAddressId"]) if order["shippingAddressId"] else None
    hsn_code  = _get_hsn_codes_for_order(db, order_id)
    total_qty = _get_order_item_count(db, order_id)

    return {
        "orderNumber":       order["orderNumber"],
        "consigneeName":     full_name,
        "consigneePhone":    drop_addr["phone"]       if drop_addr else None,
        "consigneeAddress":  drop_addr["addressLine"] if drop_addr else None,
        "consigneePinCode":  drop_addr["pinCode"]     if drop_addr else None,
        "addressType":       drop_addr["pinCode"]     if drop_addr else None,
        "consigneeCity":     drop_addr["city"]        if drop_addr else "",
        "consigneeState":    drop_addr["stateName"]   if drop_addr else "",
        "hsnCode":           hsn_code,
        "codAmount":         float(order["totalAmount"] or 0),
        "invoiceNumber":     invoice["invoiceNumber"] if invoice else "",
        "totalAmount":       float(order["totalAmount"] or 0),
        "quantity":          total_qty,
    }


def get_return_shipment_data(db: Session, order_id: int) -> dict:
    ret_row = db.execute(
        text('SELECT "Reason" FROM twam."OrderReturnInfo" WHERE "OrderId"=:id AND "DeletedInd"=false LIMIT 1'),
        {"id": order_id}
    ).fetchone()
    if not ret_row:
        raise ValueError("Order Return Info not found.")
    return_reason = ret_row[0]

    order = _get_order(db, order_id)
    if not order:
        raise ValueError("Order not found.")

    reference_order_id = order.get("referenceOrderId")
    ref_order = _get_order(db, reference_order_id) if reference_order_id else None
    if not ref_order:
        raise ValueError("Reference Order not found.")

    invoice   = _get_invoice(db, reference_order_id)
    full_name = _get_user_full_name(db, ref_order["userProfileId"] or "")
    total_qty = _get_order_item_count(db, order_id)
    total     = float(ref_order["totalAmount"] or 0)
    tax       = float(ref_order["taxAmount"] or 0)

    return {
        "consigneeName":     full_name,
        "orderNumber":       ref_order["orderNumber"],
        "invoiceNumber":     invoice["invoiceNumber"] if invoice else "",
        "invoiceDate":       invoice["createdDate"]   if invoice else datetime.now(timezone.utc),
        "totalAmount":       total,
        "taxableAmount":     tax,
        "taxValue":          total - tax,
        "consigneeGSTAmount": tax,
        "quantity":          total_qty,
        "commodityValue":    _number_to_words(tax),
        "returnReason":      return_reason,
        "productDescription": None,
        "paymentMode":       None,
        "goodsCategory":     None,
        "weight":            None,
        "codAmount":         None,
    }
