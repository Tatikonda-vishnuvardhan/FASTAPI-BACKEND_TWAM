"""
app/payment/router.py
─────────────────────
PayG payment endpoints wired into FastAPI.

  GET  /api/Payment/Callback   – browser redirect from PayG (success/fail)
  POST /api/Payment/Callback   – some PayG flows POST the result
  GET  /api/Payment/Status/{order_id} – frontend polls for payment status
  GET  /api/Payment/Config     – admin: view current PayG settings (masked)
  PUT  /api/Payment/Config     – admin: update PayG settings in the DB

Callback flow:
  1. Parse params from GET query string OR POST body
  2. FIX: PayG UAT does NOT append params to the RedirectUrl — instead we embed
     ?oid={order_id}&rid={unique_request_id} in the RedirectUrl ourselves, then
     call the PayG Detail API to get the real payment status
  3. Update Orders.state + payment fields in DB
  4. Write audit row to OrderRefund log
  5. AUTO-CREATE Ekart shipment (no admin involvement needed)
  6. Send email/SMS notification via existing ekart.notifications pipeline
  7. Redirect browser to frontend order-confirm or payment-failed page
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser
from app.orders.models import Orders, OrderTrackingStatus, OrderRefund
from app.shared.app_settings import get_setting, reload_settings
from . import payg_client

router = APIRouter(prefix="/api/Payment", tags=["Payment"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _frontend_url() -> str:
    return get_setting("frontend_base_url", "http://localhost:5173")


def _record_payment_log(
    db: Session,
    order_id: int,
    order_key_id: str,
    unique_request_id: str,
    payload: dict,
) -> None:
    """Write an audit row to the OrderRefund table."""
    try:
        merch_key_id_str = get_setting("payg_merchant_key_id", "0")
        merch_key_id = int(merch_key_id_str) if merch_key_id_str.isdigit() else 0
        log = OrderRefund(
            orderId                  = order_id,
            orderKeyId               = order_key_id,
            merchanKeyId             = merch_key_id,
            uniqueRequestId          = unique_request_id,
            orderStatus              = payload.get("OrderStatus", ""),
            paymentStatus            = payload.get("PaymentStatus"),
            paymentTransactionId     = payload.get("PaymentTransactionId", ""),
            paymentResponseCode      = payload.get("PaymentResponseCode"),
            paymentReasonCode        = payload.get("PaymentReasonCode", ""),
            paymentTransactionRefNo  = payload.get("PaymentTransactionRefNo", ""),
            paymentMethod            = payload.get("PaymentMethod", ""),
            paymentAccount           = payload.get("PaymentAccount", ""),
            createdDate              = datetime.now(timezone.utc),
            modifiedDate             = datetime.now(timezone.utc),
            deletedInd               = False,
        )
        db.add(log)
    except Exception as exc:
        print(f"[Payment] OrderRefund log failed for order {order_id}: {exc}")


def _update_order_after_payment(
    db: Session,
    order: Orders,
    response_code: int,
    payload: dict,
) -> None:
    """Update order state + payment columns from PayG callback data."""
    new_state = payg_client.payment_code_to_order_state(response_code)
    order.state                   = new_state
    order.paymentMethod           = payload.get("PaymentMethod") or order.paymentMethod
    order.paymentAccount          = payload.get("PaymentAccount") or order.paymentAccount
    order.paymentTransactionId    = payload.get("PaymentTransactionId", "")
    order.paymentTransactionRefNo = payload.get("PaymentTransactionRefNo", "")
    order.orderKeyId              = payload.get("OrderKeyId") or order.orderKeyId
    order.modifiedDate            = datetime.now(timezone.utc)
    db.add(order)
    db.add(OrderTrackingStatus(
        orderId     = order.orderId,
        status      = new_state,
        createdDate = datetime.now(timezone.utc),
    ))


def _send_payment_notification(db: Session, order_id: int, success: bool) -> None:
    try:
        if success:
            from app.ekart.notifications import send_order_placed_notification
            send_order_placed_notification(db, order_id)
    except Exception as exc:
        print(f"[Payment] Notification error for order {order_id}: {exc}")


def _enrich_params_via_detail_api(
    oid: str,
    rid: str,
) -> dict:
    """
    FIX: PayG UAT does not append params to the RedirectUrl.
    We embed ?oid=<order_id>&rid=<unique_request_id> in the RedirectUrl ourselves,
    then call the PayG Detail API here to get the real payment status.

    Returns a params dict shaped like a normal PayG callback payload so the
    rest of the callback handler works unchanged.
    """
    detail: dict = {}
    try:
        detail = payg_client.get_payg_order_detail(unique_request_id=rid)
        print(f"[Payment] Detail API response for rid={rid}: "
              f"code={detail.get('PaymentResponseCode')} status={detail.get('OrderStatus')}")
    except Exception as exc:
        print(f"[Payment] Detail API lookup failed for rid={rid}: {exc}")
        return {}

    # Extract transaction details from nested list
    txn_list = detail.get("OrderPaymentTransactionDetail") or []
    txn       = txn_list[0] if txn_list else {}

    return {
        "UserDefined1":          oid,
        "OrderKeyId":            detail.get("OrderKeyId", ""),
        "UniqueRequestId":       detail.get("UniqueRequestId", rid),
        "PaymentResponseCode":   detail.get("PaymentResponseCode", -1),
        "PaymentStatus":         detail.get("PaymentStatus"),
        "OrderStatus":           detail.get("OrderStatus", ""),
        "PaymentMethod":         detail.get("PaymentMethod") or txn.get("PaymentMethod", ""),
        "PaymentAccount":        detail.get("PaymentAccount") or txn.get("PaymentAccount", ""),
        "PaymentTransactionId":  str(txn.get("TransactionId", "")),
        "PaymentTransactionRefNo": str(txn.get("TransactionId", "")),
        "PaymentReasonCode":     txn.get("ResponseText", ""),
        "MID":                   get_setting("payg_mid"),
        "OrderAmount":           str(detail.get("OrderAmount", "")),
        # No HashData — UAT mode skips hash verification anyway
    }


# ── AUTO EKART SHIPMENT (no admin required) ────────────────────────────────

async def _auto_create_ekart_shipment(db: Session, order_id: int) -> None:
    """
    Called automatically after a successful payment — creates Ekart shipment
    without any admin involvement.

    Mirrors the logic in ekart/router.py::create_shipment but runs internally.
    """
    try:
        from app.ekart.client import get_ekart_client_for_db
        from app.ekart.schemas import (
            CreateShipmentRequest,
            EkartAddress,
            EkartShipmentItem,
        )
        from app.ekart.notifications import send_order_shipped_notification

        # ── Fetch order + delivery address ────────────────────────────────
        row = db.execute(text("""
            SELECT
                o."OrderId", o."OrderNumber", o."TotalAmount", o."State",
                o."TrackingId", o."PaymentMethod", o."DeliveryCharge",
                a."Name", a."Phone", a."AddressLine", a."City",
                a."PinCode", s."StateName", c."CountryName",
                p."Email"
            FROM twam."Orders" o
            LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
            LEFT JOIN mdm."State" s    ON s."StateId"  = a."StateId"
            LEFT JOIN mdm."Country" c  ON c."CountryId" = a."CountryId"
            LEFT JOIN twam."People" p  ON p."UserProfileId" = o."UserProfileId"
            WHERE o."OrderId" = :oid AND o."DeletedInd" = false
        """), {"oid": order_id}).fetchone()

        if not row:
            print(f"[Payment→Ekart] Order {order_id} not found — skipping shipment creation")
            return

        order = {
            "order_id":       row[0],
            "order_number":   row[1] or str(row[0]),
            "total_amount":   float(row[2]) if row[2] else 0,
            "state":          row[3],
            "tracking_id":    row[4],
            "payment_mode":   row[5] or "PREPAID",
            "delivery_charge":float(row[6]) if row[6] else 0,
            "name":           row[7] or "Customer",
            "phone":          row[8] or "",
            "address_line":   row[9] or "",
            "city":           row[10] or "",
            "state_name":     row[12] or "",
            "pincode":        row[11] or "",
            "country":        row[13] or "India",
            "email":          row[14],
        }

        # Skip if shipment already created
        if order["tracking_id"]:
            print(f"[Payment→Ekart] Order {order_id} already has tracking_id={order['tracking_id']} — skip")
            return

        # Skip non-eligible states (shouldn't happen here but guard anyway)
        if order["state"] in ("Shipped", "Delivered", "Cancelled"):
            print(f"[Payment→Ekart] Order {order_id} in state '{order['state']}' — skip")
            return

        # ── Fetch order items ─────────────────────────────────────────────
        item_rows = db.execute(text("""
            SELECT
                p."Name", p."SKU", oi."Quantity", oi."Price",
                thc."HSNCode"
            FROM twam."OrderItems" oi
            LEFT JOIN twam."Products" p ON p."ProductId" = oi."ProductId"
            LEFT JOIN twam."TaxHSNCode" thc ON thc."TaxHSNCodeId" = p."TaxHSNCodeId"
            WHERE oi."OrderId" = :oid AND oi."DeletedInd" = false
        """), {"oid": order_id}).fetchall()

        items = [
            EkartShipmentItem(
                name=r[0] or "Product",
                sku=r[1],
                quantity=r[2] or 1,
                price=float(r[3]) if r[3] else 0,
                hsn_code=r[4],
            )
            for r in item_rows
        ]

        # ── Build and send Ekart request ──────────────────────────────────
        request = CreateShipmentRequest(
            order_id=        order["order_id"],
            order_number=    order["order_number"],
            consignee_name=  order["name"],
            consignee_phone= order["phone"],
            consignee_address=EkartAddress(
                name=          order["name"],
                phone=         order["phone"],
                address_line1= order["address_line"],
                city=          order["city"],
                state=         order["state_name"],
                pincode=       order["pincode"],
                country=       order["country"],
            ),
            payment_mode="COD" if order["payment_mode"] == "COD" else "PREPAID",
            cod_amount=order["total_amount"] if order["payment_mode"] == "COD" else None,
            total_amount=order["total_amount"],
            items=items,
        )

        client = get_ekart_client_for_db(db)
        result = await client.create_shipment(request)

        if not result.success:
            print(f"[Payment→Ekart] Shipment creation FAILED for order {order_id}: {result.error_message}")
            # Order stays "Confirmed" — admin can retry manually via /api/Ekart/CreateShipment
            return

        tracking_id  = result.awb_number
        tracking_url = result.tracking_url

        print(f"[Payment→Ekart] Shipment created for order {order_id}: tracking_id={tracking_id}")

        # ── Update DB ─────────────────────────────────────────────────────
        db.execute(text("""
            UPDATE twam."Orders"
            SET "TrackingId"    = :tid,
                "State"         = 'Processing',
                "IsShipped"     = true,
                "DeliveryAgent" = 'EKart',
                "ModifiedDate"  = :now
            WHERE "OrderId" = :oid
        """), {"tid": tracking_id, "oid": order_id, "now": datetime.now(timezone.utc)})

        db.add(OrderTrackingStatus(
            orderId=order_id,
            status="Processing",
            createdDate=datetime.now(timezone.utc),
        ))
        db.commit()

        # ── Notify customer ───────────────────────────────────────────────
        await send_order_shipped_notification(db, order_id)

    except Exception as exc:
        print(f"[Payment→Ekart] Unexpected error for order {order_id}: {exc}")
        # Don't crash the callback — order is already "Confirmed", admin can retry


# ── Callback ───────────────────────────────────────────────────────────────

@router.get("/Callback",  include_in_schema=True)
@router.post("/Callback", include_in_schema=True)
async def payment_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    PayG redirects the user's browser here after payment (GET or POST).
    Processes the result, auto-creates Ekart shipment, and redirects to React.
    """
    # ── 1. Parse whatever params came in ─────────────────────────────────
    params: dict = {}
    if request.method == "GET":
        params = dict(request.query_params)
    else:
        ct = request.headers.get("content-type", "")
        if "application/json" in ct:
            try:
                params = await request.json()
            except Exception:
                params = {}
        else:
            try:
                form = await request.form()
                params = dict(form)
            except Exception:
                params = {}

    print(f"[Payment] Callback raw params: {json.dumps(params, default=str)}")

    # ── 2. FIX: If PayG sent no payment params (UAT behaviour), use our
    #           embedded oid/rid to call the Detail API instead ────────────
    oid = params.get("oid", "")   # our own param embedded in redirect URL
    rid = params.get("rid", "")   # our own param embedded in redirect URL

    payg_gave_us_params = bool(
        params.get("PaymentResponseCode") is not None
        or params.get("OrderKeyId")
        or params.get("UserDefined1")
    )

    if not payg_gave_us_params and (oid or rid):
        print(f"[Payment] PayG sent no params — calling Detail API (oid={oid}, rid={rid})")
        enriched = _enrich_params_via_detail_api(oid, rid)
        if enriched:
            params = enriched
            print(f"[Payment] Enriched params: {json.dumps(params, default=str)}")

    # ── 3. Find the order ─────────────────────────────────────────────────
    order_id_str = params.get("UserDefined1") or oid or ""
    order_key_id = params.get("OrderKeyId", "")
    unique_req_id = params.get("UniqueRequestId", "") or rid

    order: Optional[Orders] = None
    if order_id_str:
        try:
            order = db.query(Orders).filter(
                Orders.orderId    == int(order_id_str),
                Orders.deletedInd == False,
            ).first()
        except Exception:
            pass

    if order is None and order_key_id:
        order = db.query(Orders).filter(
            Orders.orderKeyId  == order_key_id,
            Orders.deletedInd  == False,
        ).first()

    # Last resort: look up by UniqueRequestId stored in paymentTransactionRefNo
    if order is None and unique_req_id:
        order = db.query(Orders).filter(
            Orders.paymentTransactionRefNo == unique_req_id,
            Orders.deletedInd              == False,
        ).first()

    if order is None:
        print(f"[Payment] Callback: order not found — oid={oid}, rid={rid}, params={params}")
        return RedirectResponse(
            url         = f"{_frontend_url()}/user-products/payment-callback?status=error&message=Order+not+found",
            status_code = 302,
        )

    order_id = order.orderId

    # ── 4. Hash verification (skipped in UAT mode) ────────────────────────
    is_uat  = get_setting("payg_mode", "uat").lower() == "uat"
    hash_ok = payg_client.verify_callback_hash(params)
    if not is_uat and not hash_ok:
        print(f"[Payment] Callback: hash mismatch for order {order_id}")
        return RedirectResponse(
            url         = f"{_frontend_url()}/user-products/payment-callback?status=error&orderId={order_id}&message=Invalid+signature",
            status_code = 302,
        )

    # ── 5. Process response code ──────────────────────────────────────────
    try:
        response_code = int(params.get("PaymentResponseCode", -1))
    except (ValueError, TypeError):
        response_code = -1

    success = (response_code == 1)
    print(f"[Payment] Order {order_id} → PaymentResponseCode={response_code}, success={success}")

    try:
        _update_order_after_payment(db, order, response_code, params)
        _record_payment_log(db, order_id, order_key_id, unique_req_id, params)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[Payment] DB update failed for order {order_id}: {exc}")

    # ── 6. Auto-create Ekart shipment on successful payment ────────────────
    # No admin needed — runs in background so the redirect is instant
    if success:
        print(f"[Payment] Scheduling auto Ekart shipment for order {order_id}")
        background_tasks.add_task(_auto_create_ekart_shipment, db, order_id)

    # ── 7. Notify customer ─────────────────────────────────────────────────
    _send_payment_notification(db, order_id, success)

    # ── 8. Redirect user ──────────────────────────────────────────────────
    if success:
        redirect_url = f"{_frontend_url()}/user-products/order-confirm/{order_id}?payment=success"
    else:
        reason = params.get("PaymentReasonCode", "declined")
        redirect_url = (
            f"{_frontend_url()}/user-products/payment-callback"
            f"?status=failed&orderId={order_id}&code={response_code}&reason={reason}"
        )

    return RedirectResponse(url=redirect_url, status_code=302)


# ── Status poll ────────────────────────────────────────────────────────────

@router.get("/Status/{order_id}")
def get_payment_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Frontend can poll this to get the latest payment status.
    Also calls PayG detail API for a live update when an orderKeyId exists.
    """
    order = db.query(Orders).filter(
        Orders.orderId    == order_id,
        Orders.deletedInd == False,
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")

    if current_user.role_id not in Roles.STAFF and order.userProfileId != current_user.user_id:
        raise HTTPException(403, "Not authorised")

    local_state = order.state or "Pending"
    payg_detail: dict = {}

    if order.orderKeyId or order.paymentTransactionRefNo:
        try:
            payg_detail = payg_client.get_payg_order_detail(
                order_key_id      = order.orderKeyId,
                unique_request_id = order.paymentTransactionRefNo,
            )
            live_code = payg_detail.get("PaymentResponseCode")
            if live_code is not None:
                live_state = payg_client.payment_code_to_order_state(int(live_code))
                if order.state != live_state:
                    order.state        = live_state
                    order.modifiedDate = datetime.now(timezone.utc)
                    db.add(order)
                    db.commit()
                    local_state = live_state
        except Exception as exc:
            print(f"[Payment] Live status check failed: {exc}")

    return {
        "orderId":              order_id,
        "orderNumber":          order.orderNumber,
        "state":                local_state,
        "paymentMethod":        order.paymentMethod,
        "paymentTransactionId": order.paymentTransactionId,
        "paymentResponseCode":  payg_detail.get("PaymentResponseCode"),
        "paygStatus":           payg_detail.get("OrderStatus"),
    }


# ── Admin: view / update PayG config ──────────────────────────────────────

class PaygConfigResponse(BaseModel):
    payg_mode:            str
    payg_mid:             str
    payg_auth_key:        str   # masked
    payg_auth_token:      str   # masked
    payg_secure_hash:     str   # masked
    payg_merchant_key_id: str
    payg_redirect_url:    str
    frontend_base_url:    str


class PaygConfigUpdate(BaseModel):
    payg_mode:            Optional[str] = None
    payg_mid:             Optional[str] = None
    payg_auth_key:        Optional[str] = None
    payg_auth_token:      Optional[str] = None
    payg_secure_hash:     Optional[str] = None
    payg_merchant_key_id: Optional[str] = None
    payg_redirect_url:    Optional[str] = None
    frontend_base_url:    Optional[str] = None


def _mask(v: str) -> str:
    if not v or len(v) <= 8:
        return "****"
    return v[:4] + "****" + v[-4:]


@router.get(
    "/Config",
    response_model = PaygConfigResponse,
    dependencies   = [Depends(require_roles(Roles.SUPER_ADMIN))],
)
def get_payg_config():
    """Admin: view current PayG settings (secrets are masked)."""
    return PaygConfigResponse(
        payg_mode            = get_setting("payg_mode", "uat"),
        payg_mid             = get_setting("payg_mid", ""),
        payg_auth_key        = _mask(get_setting("payg_auth_key", "")),
        payg_auth_token      = _mask(get_setting("payg_auth_token", "")),
        payg_secure_hash     = _mask(get_setting("payg_secure_hash", "")),
        payg_merchant_key_id = get_setting("payg_merchant_key_id", ""),
        payg_redirect_url    = get_setting("payg_redirect_url", ""),
        frontend_base_url    = get_setting("frontend_base_url", "http://localhost:5173"),
    )


@router.put(
    "/Config",
    dependencies = [Depends(require_roles(Roles.SUPER_ADMIN))],
)
def update_payg_config(
    data: PaygConfigUpdate,
    db: Session = Depends(get_db),
):
    """Admin: update one or more PayG settings in the DB."""
    from app.common.models import AppSettings

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    now = datetime.now(timezone.utc)

    for key, value in updates.items():
        row = (
            db.query(AppSettings)
            .filter(AppSettings.key == key, AppSettings.deletedInd == False)
            .first()
        )
        if row:
            row.value        = value
            row.modifiedDate = now
        else:
            db.add(AppSettings(
                key          = key,
                value        = value,
                description  = f"PayG setting: {key}",
                isActive     = True,
                createdDate  = now,
                modifiedDate = now,
                deletedInd   = False,
            ))

    db.commit()
    reload_settings(db)
    return {"success": True, "updated": list(updates.keys())}