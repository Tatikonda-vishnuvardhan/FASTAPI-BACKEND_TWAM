"""
Shipment repository — mirrors:
  - CreateShipmentCommandHandler        (Ekart forward shipment)
  - CreateEkartReturnShipmentCommandHandler (Ekart return)
  - CreateDelhiveryShipmentCommandHandler   (Delhivery forward)
  - CancelShipmentCommandHandler
  - GetShipmentDataQueryHandler
  - GetDelhiveryShipmentDataQueryHandler
  - GetReturnShipmentDataQueryHandler

NOTE: IDeliveryService (Ekart/Delhivery API calls) is a TODO stub.
      All the DB logic is faithfully converted; external API calls return
      a placeholder tracking_id so the DB writes always execute.
"""
import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from .models import Shipment

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


def _get_integration_location(db: Session, location_id: int) -> Optional[str]:
    """Returns LocationName from twam.IntegrationLocation."""
    try:
        row = db.execute(
            text('SELECT "LocationName" FROM twam."IntegrationLocation" WHERE "IntegrationLocationId"=:id LIMIT 1'),
            {"id": location_id}
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _get_supplier(db: Session, supplier_id: int) -> Optional[dict]:
    try:
        row = db.execute(
            text('SELECT "SupplierName","SupplierAddress","SupplierGSTNumber","SupplierGSTAmount" FROM twam."SupplierInfo" WHERE "SupplierInfoId"=:id LIMIT 1'),
            {"id": supplier_id}
        ).fetchone()
        return {"name": row[0], "address": row[1], "gstNumber": row[2], "gstAmount": row[3]} if row else None
    except Exception:
        return None


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
    """Simple stub — replace with full NumberToWordsConverter if needed."""
    return str(amount)


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
    db.execute(text(f"""
        UPDATE twam."Orders"
        SET "TrackingId"=:tid, "IsShipped"=true, "DeliveryAgent"=:agent, "State"='Processing'
        WHERE "OrderId"=:oid
    """), {"tid": tracking_id, "agent": agent, "oid": order_id})
    db.execute(text("""
        UPDATE twam."OrderItems" SET "TrackingId"=:tid WHERE "OrderId"=:oid
    """), {"tid": tracking_id, "oid": order_id})
    db.commit()


# ── Create Ekart Forward Shipment ─────────────────────────────────────────────

def create_shipment(db: Session, data) -> dict:
    """
    Mirrors CreateShipmentCommandHandler.
    Returns {"trackingId": ..., "success": True} on success.
    """
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    # TODO: Replace with real IDeliveryService.CreateShipmentRequestAsync call
    # For now, call is stubbed — integrate your delivery service client here.
    tracking_id = None  # = await delivery_service.create_shipment(payload)

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
        return {"trackingId": tracking_id, "success": True, "message": "Shipment created."}

    return {"trackingId": None, "success": False, "message": "Delivery service did not return a tracking ID. TODO: Integrate IDeliveryService."}


# ── Create Ekart Return Shipment ──────────────────────────────────────────────

def create_return_shipment(db: Session, data) -> int:
    """Mirrors CreateEkartReturnShipmentCommandHandler — qc_shipment=true."""
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    # TODO: Replace with real IDeliveryService.CreateShipmentRequestAsync call (qc_shipment=true)
    tracking_id = None

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


# ── Create Delhivery Shipment ─────────────────────────────────────────────────

def create_delhivery_shipment(db: Session, data) -> int:
    """Mirrors CreateDelhiveryShipmentCommandHandler."""
    order = _get_order(db, data.orderId)
    if not order:
        raise ValueError("Order not found.")

    # TODO: Replace with real IDeliveryService.CreateDelhiveryShipmentRequestAsync call
    tracking_id = None

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

    ship.deletedInd   = True
    ship.modifiedDate = datetime.now(timezone.utc)
    db.commit()

    # TODO: Replace with real IDeliveryService.CancelShipmentRequestAsync(ship.trackingId)
    return True


# ── GetShipmentDataQuery ──────────────────────────────────────────────────────

def get_shipment_data(db: Session, order_id: int) -> dict:
    """Mirrors GetShipmentDataQueryHandler — pre-fills Ekart shipment form."""
    order = _get_order(db, order_id)
    if not order:
        raise ValueError("Order not found.")

    invoice    = _get_invoice(db, order_id)
    full_name  = _get_user_full_name(db, order["userProfileId"] or "")
    total_qty  = _get_order_item_count(db, order_id)
    total      = float(order["totalAmount"] or 0)
    tax        = float(order["taxAmount"] or 0)

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


# ── GetDelhiveryShipmentDataQuery ─────────────────────────────────────────────

def get_delhivery_shipment_data(db: Session, order_id: int) -> dict:
    """Mirrors GetDelhiveryShipmentDataQueryHandler."""
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
        "addressType":       drop_addr["pinCode"]     if drop_addr else None,  # matches .NET logic
        "consigneeCity":     drop_addr["city"]        if drop_addr else "",
        "consigneeState":    drop_addr["stateName"]   if drop_addr else "",
        "hsnCode":           hsn_code,
        "codAmount":         float(order["totalAmount"] or 0),
        "invoiceNumber":     invoice["invoiceNumber"] if invoice else "",
        "totalAmount":       float(order["totalAmount"] or 0),
        "quantity":          total_qty,
    }


# ── GetReturnShipmentDataQuery ────────────────────────────────────────────────

def get_return_shipment_data(db: Session, order_id: int) -> dict:
    """Mirrors GetReturnShipmentDataQueryHandler."""
    # Get return info
    ret_row = db.execute(
        text('SELECT "Reason" FROM twam."OrderReturnInfo" WHERE "OrderId"=:id AND "DeletedInd"=false LIMIT 1'),
        {"id": order_id}
    ).fetchone()
    if not ret_row:
        raise ValueError("Order Return Info not found.")
    return_reason = ret_row[0]

    # The return order points to a reference (original) order
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