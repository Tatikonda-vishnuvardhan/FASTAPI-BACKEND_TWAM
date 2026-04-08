"""
Ekart Webhooks Router
─────────────────────
Endpoints for receiving callbacks from Ekart when shipment status changes.

Webhook secret change
─────────────────────
EKART_WEBHOOK_SECRET is no longer read from os.getenv() at module load time.
It is now fetched from the AppSettings DB cache on every request so it can
be rotated without restarting the server.

AppSettings key: "ekart_webhook_secret"
Default:         "" (empty = dev mode, no signature verification)

Setup in Ekart portal:
  URL:    https://yourdomain.com/api/webhooks/ekart
  Topics: track_updated
  Secret: set via Admin > App Settings > ekart_webhook_secret
"""

import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from app.orders.models import Orders, OrderTrackingStatus
from app.ekart.schemas import EkartWebhookPayload, EKART_STATUS_TEXT_TO_ORDER
from app.ekart.notifications import (
    send_order_status_notification,
    send_delivery_confirmation,
    send_out_for_delivery_notification,
)

router = APIRouter(
    prefix="/api/webhooks",
    tags=["Webhooks"],
)


# ── Webhook signature verification ───────────────────────────────────────────

def _get_webhook_secret() -> str:
    """
    Return the current Ekart webhook HMAC secret from the AppSettings cache.
    Empty string → dev/test mode (no verification).
    """
    from app.shared.app_settings import get_setting
    return get_setting("ekart_webhook_secret", "")


def verify_ekart_signature(request: Request, body: bytes) -> bool:
    """
    Verify the webhook request is genuinely from Ekart using HMAC-SHA256.
    Ekart sends the signature in the X-Ekart-Signature header.
    If the secret is empty we allow all requests through (dev mode).
    """
    secret = _get_webhook_secret()
    if not secret:
        return True  # Dev mode — no secret configured

    signature = request.headers.get("X-Ekart-Signature", "")
    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


# ── Main Webhook Endpoint ─────────────────────────────────────────────────────

@router.post("/ekart")
async def ekart_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive shipment status updates from Ekart (track_updated topic).
    Updates order state and dispatches customer notifications.
    """
    body = await request.body()

    if not verify_ekart_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        data    = json.loads(body)
        payload = EkartWebhookPayload(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # ── Find the order ────────────────────────────────────────────────────────
    order = db.query(Orders).filter(
        Orders.trackingId == payload.awb_number,
        Orders.deletedInd == False,
    ).first()

    if not order and payload.order_number:
        order = db.query(Orders).filter(
            Orders.orderNumber == payload.order_number,
            Orders.deletedInd  == False,
        ).first()

    if not order:
        print(f"[Webhook] Order not found for wbn={payload.awb_number} "
              f"orderNumber={payload.order_number}")
        return {"status": "ignored", "reason": "Order not found"}

    # ── Map status → order state ──────────────────────────────────────────────
    new_state  = EKART_STATUS_TEXT_TO_ORDER.get(payload.status)
    if not new_state:
        print(f"[Webhook] Unknown Ekart status '{payload.status}' for order "
              f"{order.orderId} — tracking recorded, state unchanged")
        new_state = order.state

    old_state  = order.state
    event_time = payload.status_datetime or datetime.now(timezone.utc)

    # ── Update order ──────────────────────────────────────────────────────────
    if new_state != old_state:
        order.state        = new_state
        order.modifiedDate = datetime.now(timezone.utc)
        if new_state == "Delivered" and not order.deliveredDate:
            order.deliveredDate = event_time

    db.add(OrderTrackingStatus(
        orderId     = order.orderId,
        status      = payload.status,
        createdDate = event_time,
    ))
    db.commit()

    # ── Background notifications ──────────────────────────────────────────────
    if new_state != old_state:
        background_tasks.add_task(
            _process_notifications,
            db, order.orderId, old_state, new_state, payload,
        )

    return {
        "status":       "processed",
        "order_id":     order.orderId,
        "old_state":    old_state,
        "new_state":    new_state,
        "ekart_status": payload.status,
    }


# ── Bulk Tracking Endpoint ────────────────────────────────────────────────────

class BulkTrackingItem(BaseModel):
    wbn:       str
    status:    str
    timestamp: int  # ms epoch


class BulkTrackingPayload(BaseModel):
    items: list[BulkTrackingItem]


@router.post("/ekart/bulk")
async def ekart_bulk_webhook(
    payload:          BulkTrackingPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Receive bulk tracking updates from Ekart (hourly batch mode)."""
    results = []

    for item in payload.items:
        order = db.query(Orders).filter(
            Orders.trackingId == item.wbn,
            Orders.deletedInd == False,
        ).first()

        if not order:
            results.append({"wbn": item.wbn, "status": "not_found"})
            continue

        new_state  = EKART_STATUS_TEXT_TO_ORDER.get(item.status, order.state)
        old_state  = order.state
        event_time = datetime.fromtimestamp(item.timestamp / 1000, tz=timezone.utc)

        if new_state != old_state:
            order.state        = new_state
            order.modifiedDate = datetime.now(timezone.utc)
            if new_state == "Delivered" and not order.deliveredDate:
                order.deliveredDate = event_time

        db.add(OrderTrackingStatus(
            orderId     = order.orderId,
            status      = item.status,
            createdDate = event_time,
        ))

        results.append({
            "wbn":       item.wbn,
            "order_id":  order.orderId,
            "status":    "updated" if new_state != old_state else "no_change",
            "new_state": new_state,
        })

    db.commit()
    return {"processed": len(results), "results": results}


# ── Notification dispatcher ───────────────────────────────────────────────────

async def _process_notifications(
    db:        Session,
    order_id:  int,
    old_state: str,
    new_state: str,
    payload:   EkartWebhookPayload,
) -> None:
    try:
        if new_state == "Out for Delivery":
            await send_out_for_delivery_notification(db, order_id)
        elif new_state == "Delivered":
            await send_delivery_confirmation(
                db, order_id, pod_image_url=payload.pod_image_url,
            )
        else:
            send_order_status_notification(db, order_id, new_state)
    except Exception as e:
        print(f"[Webhook] Notification error for order {order_id} "
              f"({old_state} → {new_state}): {e}")


# ── Health check ──────────────────────────────────────────────────────────────

@router.get("/ekart/health")
async def ekart_webhook_health():
    return {
        "status":    "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service":   "twam-ecommerce",
    }
