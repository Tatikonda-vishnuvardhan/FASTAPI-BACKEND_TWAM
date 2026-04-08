"""
app/ekart/router.py  — Ekart Elite Logistics Router
─────────────────────────────────────────────────────
All Ekart API features exposed as REST endpoints:
  POST   /api/Ekart/CreateShipment          — single forward shipment
  POST   /api/Ekart/BulkShipment            — bulk forward shipments (multiple orders)
  POST   /api/Ekart/CreateReturnShipment    — reverse/return shipment
  DELETE /api/Ekart/CancelShipment          — cancel shipment on Ekart
  GET    /api/Ekart/Track/{tracking_id}     — live tracking
  POST   /api/Ekart/UpdateStatus            — manual order status update
  POST   /api/Ekart/DownloadLabel           — download shipping label PDF
  POST   /api/Ekart/DownloadManifest        — download manifest PDF
  POST   /api/Ekart/NDRAction               — Non-Delivery Report action
  GET    /api/Ekart/Serviceability/{pincode}— serviceability check v2
  POST   /api/Ekart/ServiceabilityV3        — serviceability check v3
  POST   /api/Ekart/ShippingEstimate        — shipping rate calculator
  POST   /api/Ekart/SetDispatchDate         — set preferred dispatch date
  GET    /api/Ekart/CODReport               — COD cash collection report
  GET    /api/Ekart/Config                  — view ShipmentConfigurations
  PUT    /api/Ekart/Config/{id}             — update ShipmentConfigurations
  GET    /api/Ekart/Readiness               — check live-readiness
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from database import get_db
from app.auth.dependencies import get_current_user, get_current_admin_user
from app.orders.models import Orders, OrderTrackingStatus
from app.ekart.client import get_ekart_client_for_db
from app.ekart.schemas import (
    CreateShipmentRequest,
    CreateReturnShipmentRequest,
    EkartAddress,
    EkartShipmentItem,
    CancelShipmentRequest,
)
from app.ekart.notifications import (
    send_order_shipped_notification,
    send_order_cancelled_notification,
    send_return_initiated_notification,
    send_order_status_notification,
)

router = APIRouter(prefix="/api/Ekart", tags=["Ekart Logistics"])


# ── Request / Response Models ─────────────────────────────────────────────────

class CreateShipmentInput(BaseModel):
    order_id: int
    manual_tracking_id: Optional[str] = None
    delivery_days: Optional[int] = None


class BulkShipmentInput(BaseModel):
    order_ids: List[int]


class CreateReturnInput(BaseModel):
    order_id: int
    return_reason: str


class UpdateOrderStatusInput(BaseModel):
    order_id: int
    status: str
    tracking_id: Optional[str] = None
    remarks: Optional[str] = None


class CancelShipmentInput(BaseModel):
    order_id: int
    reason: Optional[str] = "Customer requested cancellation"


class LabelDownloadInput(BaseModel):
    awb_numbers: List[str]
    json_only: bool = False


class ManifestInput(BaseModel):
    awb_numbers: List[str]


class NDRActionInput(BaseModel):
    tracking_id: str
    action: str  # "RE_ATTEMPT" | "RTO" | "CONFIRM_DELIVERY"
    remarks: Optional[str] = ""
    preferred_date: Optional[str] = None  # "YYYY-MM-DD"


class ServiceabilityV3Input(BaseModel):
    pickup_pincode: str
    drop_pincode: str
    weight: float = 0.5
    length: float = 30
    width: float = 25
    height: float = 5


class ShippingEstimateInput(BaseModel):
    pickup_pincode: str
    drop_pincode: str
    weight: float = 0.5
    payment_mode: str = "Prepaid"  # "Prepaid" | "COD"
    cod_amount: float = 0


class DispatchDateInput(BaseModel):
    awb_numbers: List[str]
    dispatch_date: str  # "YYYY-MM-DD"


class ShipmentConfigUpdate(BaseModel):
    clientId: Optional[str] = None
    accessTokenURL: Optional[str] = None
    createShipmentURL: Optional[str] = None
    cancelShipmentURL: Optional[str] = None
    trackShipmentURL: Optional[str] = None
    wayBillURL: Optional[str] = None
    userName: Optional[str] = None
    password: Optional[str] = None
    returnName: Optional[str] = None
    returnPhone: Optional[str] = None
    returnAddressLine1: Optional[str] = None
    returnAddressLine2: Optional[str] = None
    returnCity: Optional[str] = None
    returnState: Optional[str] = None
    returnPinCode: Optional[str] = None
    returnCountry: Optional[str] = None


class ShipmentResponse(BaseModel):
    success: bool
    order_id: Optional[int] = None
    tracking_id: Optional[str] = None
    tracking_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_order_with_address(db: Session, order_id: int) -> Optional[dict]:
    row = db.execute(text("""
        SELECT
            o."OrderId", o."OrderNumber", o."TotalAmount", o."State",
            o."TrackingId", o."PaymentMethod", o."DeliveryCharge",
            a."Name", a."Phone", a."AddressLine", a."City",
            a."PinCode", s."StateName", c."CountryName",
            p."Email"
        FROM twam."Orders" o
        LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
        LEFT JOIN mdm."State" s ON s."StateId" = a."StateId"
        LEFT JOIN mdm."Country" c ON c."CountryId" = a."CountryId"
        LEFT JOIN twam."People" p ON p."UserProfileId" = o."UserProfileId"
        WHERE o."OrderId" = :order_id AND o."DeletedInd" = false
    """), {"order_id": order_id}).fetchone()

    if not row:
        return None

    return {
        "order_id":      row[0],
        "order_number":  row[1] or str(row[0]),
        "total_amount":  float(row[2]) if row[2] else 0,
        "state":         row[3],
        "tracking_id":   row[4],
        "payment_mode":  row[5] or "PREPAID",
        "delivery_charge": float(row[6]) if row[6] else 0,
        "name":          row[7],
        "phone":         row[8],
        "address_line":  row[9],
        "city":          row[10],
        "pincode":       row[11],
        "state_name":    row[12] or "",
        "country":       row[13] or "India",
        "email":         row[14],
    }


def _get_order_items_for_shipment(db: Session, order_id: int) -> list:
    rows = db.execute(text("""
        SELECT
            p."Name", p."SKU", oi."Quantity", oi."Price",
            thc."HSNCode"
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products" p ON p."ProductId" = oi."ProductId"
        LEFT JOIN twam."TaxHSNCode" thc ON thc."TaxHSNCodeId" = p."TaxHSNCodeId"
        WHERE oi."OrderId" = :order_id AND oi."DeletedInd" = false
    """), {"order_id": order_id}).fetchall()

    return [
        EkartShipmentItem(
            name=r[0] or "Product",
            sku=r[1],
            quantity=r[2] or 1,
            price=float(r[3]) if r[3] else 0,
            hsn_code=r[4],
        )
        for r in rows
    ]


def _build_return_address_from_db(db: Session) -> EkartAddress:
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
                name=          row.returnName         or "Warehouse",
                phone=         row.returnPhone         or "",
                address_line1= row.returnAddressLine1  or "",
                address_line2= row.returnAddressLine2  or None,
                city=          row.returnCity          or "",
                state=         row.returnState         or "",
                pincode=       row.returnPinCode       or "",
                country=       row.returnCountry       or "India",
            )
    except Exception as e:
        print(f"[EkartRouter] DB return address load failed: {e}")

    return EkartAddress(
        name="Warehouse",
        phone="",
        address_line1="[FILL: Configure ReturnAddressLine1 in ShipmentConfigurations]",
        city="", state="", pincode="", country="India",
    )


def _build_shipment_request(order: dict, items: list) -> CreateShipmentRequest:
    return CreateShipmentRequest(
        order_id=       order["order_id"],
        order_number=   order["order_number"],
        consignee_name= order["name"],
        consignee_phone=order["phone"] or "",
        consignee_address=EkartAddress(
            name=          order["name"] or "Customer",
            phone=         order["phone"] or "",
            address_line1= order["address_line"] or "",
            city=          order["city"] or "",
            state=         order["state_name"],
            pincode=       order["pincode"] or "",
            country=       order["country"],
        ),
        payment_mode="COD" if order["payment_mode"] == "COD" else "PREPAID",
        cod_amount=order["total_amount"] if order["payment_mode"] == "COD" else None,
        total_amount=order["total_amount"],
        items=items,
    )


# ── Create Single Shipment ────────────────────────────────────────────────────

@router.post("/CreateShipment", response_model=ShipmentResponse)
async def create_shipment(
    inp: CreateShipmentInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    order = _get_order_with_address(db, inp.order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    if order["state"] in ("Shipped", "Delivered", "Cancelled"):
        raise HTTPException(400, f"Cannot create shipment for order in '{order['state']}' state")

    if order["tracking_id"]:
        return ShipmentResponse(
            success=True, order_id=order["order_id"],
            tracking_id=order["tracking_id"],
            message="Order already has a tracking ID",
        )

    if inp.manual_tracking_id:
        tracking_id  = inp.manual_tracking_id
        tracking_url = None
    else:
        items   = _get_order_items_for_shipment(db, inp.order_id)
        request = _build_shipment_request(order, items)

        client = get_ekart_client_for_db(db)
        result = await client.create_shipment(request)

        if not result.success:
            return ShipmentResponse(
                success=False, order_id=order["order_id"],
                error=result.error_message or "Failed to create shipment",
            )

        tracking_id  = result.awb_number
        tracking_url = result.tracking_url

    db.execute(text("""
        UPDATE twam."Orders"
        SET "TrackingId" = :tid, "State" = 'Processing', "IsShipped" = true,
            "DeliveryAgent" = 'EKart', "ModifiedDate" = :now
        WHERE "OrderId" = :order_id
    """), {"tid": tracking_id, "order_id": inp.order_id, "now": datetime.now(timezone.utc)})

    db.add(OrderTrackingStatus(
        orderId=inp.order_id,
        status="Processing",
        createdDate=datetime.now(timezone.utc),
    ))
    db.commit()

    background_tasks.add_task(send_order_shipped_notification, db, inp.order_id)

    return ShipmentResponse(
        success=True, order_id=order["order_id"],
        tracking_id=tracking_id, tracking_url=tracking_url,
        message="Shipment created successfully",
    )


# ── Bulk Shipment Creation ────────────────────────────────────────────────────

@router.post("/BulkShipment")
async def create_bulk_shipments(
    inp: BulkShipmentInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Create shipments for multiple orders in one call.
    Returns per-order success/failure results.
    """
    if not inp.order_ids:
        raise HTTPException(400, "No order IDs provided")

    if len(inp.order_ids) > 50:
        raise HTTPException(400, "Maximum 50 orders per bulk request")

    # Build Ekart requests for all eligible orders
    shipment_requests = []
    skipped = []

    for order_id in inp.order_ids:
        order = _get_order_with_address(db, order_id)
        if not order:
            skipped.append({"order_id": order_id, "reason": "Not found"})
            continue
        if order["state"] in ("Shipped", "Delivered", "Cancelled"):
            skipped.append({"order_id": order_id, "reason": f"State is '{order['state']}'"})
            continue
        if order["tracking_id"]:
            skipped.append({"order_id": order_id, "reason": "Already has tracking ID", "tracking_id": order["tracking_id"]})
            continue

        items = _get_order_items_for_shipment(db, order_id)
        if not items:
            skipped.append({"order_id": order_id, "reason": "No order items"})
            continue

        shipment_requests.append(_build_shipment_request(order, items))

    if not shipment_requests:
        return {"success": False, "processed": 0, "skipped": skipped, "results": []}

    # Bulk create on Ekart (concurrent)
    client  = get_ekart_client_for_db(db)
    results = await client.create_bulk_shipments(shipment_requests)

    # Persist successful shipments
    success_count = 0
    for r in results:
        if r["success"] and r["awb_number"]:
            db.execute(text("""
                UPDATE twam."Orders"
                SET "TrackingId" = :tid, "State" = 'Processing', "IsShipped" = true,
                    "DeliveryAgent" = 'EKart', "ModifiedDate" = :now
                WHERE "OrderId" = :order_id
            """), {
                "tid": r["awb_number"],
                "order_id": r["order_id"],
                "now": datetime.now(timezone.utc),
            })
            db.add(OrderTrackingStatus(
                orderId=r["order_id"], status="Processing",
                createdDate=datetime.now(timezone.utc),
            ))
            background_tasks.add_task(send_order_shipped_notification, db, r["order_id"])
            success_count += 1

    db.commit()

    return {
        "success":   success_count > 0,
        "processed": success_count,
        "failed":    len([r for r in results if not r["success"]]),
        "skipped":   skipped,
        "results":   results,
    }


# ── Create Return Shipment ────────────────────────────────────────────────────

@router.post("/CreateReturnShipment", response_model=ShipmentResponse)
async def create_return_shipment(
    inp: CreateReturnInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    order = _get_order_with_address(db, inp.order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    if order["state"] != "Delivered":
        raise HTTPException(400, "Can only create return for delivered orders")

    items          = _get_order_items_for_shipment(db, inp.order_id)
    return_address = _build_return_address_from_db(db)

    request = CreateReturnShipmentRequest(
        order_id=       order["order_id"],
        original_awb=   order["tracking_id"] or "",
        return_reason=  inp.return_reason,
        pickup_name=    order["name"],
        pickup_phone=   order["phone"] or "",
        pickup_address= EkartAddress(
            name=          order["name"],
            phone=         order["phone"] or "",
            address_line1= order["address_line"] or "",
            city=          order["city"] or "",
            state=         order["state_name"],
            pincode=       order["pincode"] or "",
        ),
        return_address=return_address,
        items=items,
    )

    client = get_ekart_client_for_db(db)
    result = await client.create_return_shipment(request)

    if not result.success:
        return ShipmentResponse(
            success=False, order_id=order["order_id"],
            error=result.error_message or "Failed to create return shipment",
        )

    db.execute(text("""
        UPDATE twam."Orders"
        SET "State" = 'Return Initiated', "ModifiedDate" = :now
        WHERE "OrderId" = :order_id
    """), {"order_id": inp.order_id, "now": datetime.now(timezone.utc)})

    db.add(OrderTrackingStatus(
        orderId=inp.order_id, status="Return Initiated",
        createdDate=datetime.now(timezone.utc),
    ))
    db.commit()

    background_tasks.add_task(send_return_initiated_notification, db, inp.order_id, inp.return_reason)

    return ShipmentResponse(
        success=True, order_id=order["order_id"],
        tracking_id=result.awb_number, tracking_url=result.tracking_url,
        message="Return pickup scheduled",
    )


# ── Track Shipment ────────────────────────────────────────────────────────────

@router.get("/Track/{tracking_id}")
async def track_shipment(
    tracking_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.shipment.repository import track_shipment_live
    return track_shipment_live(db, tracking_id)


# ── Cancel Shipment ───────────────────────────────────────────────────────────

@router.post("/CancelShipment", response_model=ShipmentResponse)
async def cancel_shipment(
    inp: CancelShipmentInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    order = _get_order_with_address(db, inp.order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    if order["state"] in ("Delivered", "Cancelled"):
        raise HTTPException(400, f"Cannot cancel order in '{order['state']}' state")

    if order["tracking_id"]:
        client = get_ekart_client_for_db(db)
        result = await client.cancel_shipment(CancelShipmentRequest(
            awb_number=order["tracking_id"],
            reason=inp.reason or "Customer requested cancellation",
        ))
        if not result.success:
            print(f"[Ekart] Cancel warning: {result.error_message}")

    db.execute(text("""
        UPDATE twam."Orders"
        SET "State" = 'Cancelled', "Reason" = :reason, "ModifiedDate" = :now
        WHERE "OrderId" = :order_id
    """), {"reason": inp.reason, "order_id": inp.order_id, "now": datetime.now(timezone.utc)})

    db.add(OrderTrackingStatus(
        orderId=inp.order_id, status="Cancelled",
        createdDate=datetime.now(timezone.utc),
    ))
    db.commit()

    background_tasks.add_task(send_order_cancelled_notification, db, inp.order_id, inp.reason)

    return ShipmentResponse(success=True, order_id=inp.order_id, message="Shipment cancelled")


# ── Update Order Status (Admin) ───────────────────────────────────────────────

@router.post("/UpdateStatus", response_model=ShipmentResponse)
async def update_order_status(
    inp: UpdateOrderStatusInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    valid_statuses = [
        "Pending", "Confirmed", "Processing", "Shipped",
        "Out for Delivery", "Delivered", "Cancelled",
        "Return Initiated", "Returned", "Refunded"
    ]
    if inp.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    order = db.query(Orders).filter(
        Orders.orderId == inp.order_id, Orders.deletedInd == False
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")

    old_state   = order.state
    order.state = inp.status
    order.modifiedDate = datetime.now(timezone.utc)

    if inp.tracking_id:
        order.trackingId = inp.tracking_id
        order.isShipped  = True

    if inp.status == "Delivered" and not order.deliveredDate:
        order.deliveredDate = datetime.now(timezone.utc)

    db.add(OrderTrackingStatus(
        orderId=inp.order_id, status=inp.status,
        createdDate=datetime.now(timezone.utc),
    ))
    db.commit()

    if old_state != inp.status:
        background_tasks.add_task(send_order_status_notification, db, inp.order_id, inp.status)

    return ShipmentResponse(
        success=True, order_id=inp.order_id,
        tracking_id=order.trackingId,
        message=f"Order status updated to {inp.status}",
    )


# ── Download Label ────────────────────────────────────────────────────────────

@router.post("/DownloadLabel")
async def download_label(
    inp: LabelDownloadInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Download shipping label(s) as PDF (or JSON if json_only=true).
    Up to 100 AWB numbers per request.
    """
    if not inp.awb_numbers:
        raise HTTPException(400, "No AWB numbers provided")

    if len(inp.awb_numbers) > 100:
        raise HTTPException(400, "Maximum 100 AWB numbers per label request")

    client = get_ekart_client_for_db(db)
    result = await client.download_label(inp.awb_numbers, json_only=inp.json_only)

    if isinstance(result, bytes):
        # Return raw PDF
        return Response(
            content=result,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=labels.pdf"},
        )
    else:
        return result


# ── Download Manifest ─────────────────────────────────────────────────────────

@router.post("/DownloadManifest")
async def download_manifest(
    inp: ManifestInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Generate manifest for a list of AWB numbers.
    A manifest is needed before handover to Ekart courier.
    Up to 100 AWB numbers per request.
    """
    if not inp.awb_numbers:
        raise HTTPException(400, "No AWB numbers provided")

    if len(inp.awb_numbers) > 100:
        raise HTTPException(400, "Maximum 100 AWB numbers per manifest")

    client = get_ekart_client_for_db(db)
    result = await client.download_manifest(inp.awb_numbers)
    return result


# ── NDR Action ────────────────────────────────────────────────────────────────

@router.post("/NDRAction")
async def ndr_action(
    inp: NDRActionInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Take action on a Non-Delivery Report (NDR) shipment.

    ndr_action values:
      - RE_ATTEMPT    → schedule re-delivery (provide preferred_date: YYYY-MM-DD)
      - RTO           → initiate Return to Origin
      - CONFIRM_DELIVERY → mark as customer confirmed delivery
    """
    valid_actions = ["RE_ATTEMPT", "RTO", "CONFIRM_DELIVERY"]
    if inp.action not in valid_actions:
        raise HTTPException(400, f"Invalid NDR action. Must be one of: {', '.join(valid_actions)}")

    client = get_ekart_client_for_db(db)
    result = await client.action_ndr(
        tracking_id=inp.tracking_id,
        ndr_action=inp.action,
        remarks=inp.remarks or "",
        preferred_date=inp.preferred_date,
    )

    # If RTO, update order state in DB
    if inp.action == "RTO" and not result.get("error"):
        row = db.execute(
            text('SELECT "OrderId" FROM twam."Orders" WHERE "TrackingId" = :tid AND "DeletedInd" = false LIMIT 1'),
            {"tid": inp.tracking_id}
        ).fetchone()
        if row:
            db.execute(text("""
                UPDATE twam."Orders"
                SET "State" = 'Return Initiated', "ModifiedDate" = :now
                WHERE "OrderId" = :oid
            """), {"oid": row[0], "now": datetime.now(timezone.utc)})
            db.add(OrderTrackingStatus(
                orderId=row[0], status="Return Initiated",
                createdDate=datetime.now(timezone.utc),
            ))
            db.commit()

    return {"success": not result.get("error"), "tracking_id": inp.tracking_id, "result": result}


# ── Serviceability V2 ─────────────────────────────────────────────────────────

@router.get("/Serviceability/{pincode}")
async def check_serviceability(
    pincode: str,
    db: Session = Depends(get_db),
):
    """
    Check if a pincode is serviceable by Ekart (v2 API).
    Returns COD availability and forward/reverse serviceability.
    """
    if len(pincode) != 6 or not pincode.isdigit():
        return {"serviceable": False, "pincode": pincode, "message": "Invalid pincode (must be 6 digits)"}

    client = get_ekart_client_for_db(db)
    result = await client.check_serviceability_v2(pincode)
    return result


# ── Serviceability V3 ─────────────────────────────────────────────────────────

@router.post("/ServiceabilityV3")
async def check_serviceability_v3(
    inp: ServiceabilityV3Input,
    db: Session = Depends(get_db),
):
    """
    Check available courier partners for a pickup→drop pincode pair (v3 API).
    Returns list of courier options with estimated delivery days.
    """
    client = get_ekart_client_for_db(db)
    result = await client.check_serviceability_v3(
        pickup_pincode=inp.pickup_pincode,
        drop_pincode=inp.drop_pincode,
        weight=inp.weight,
        length=inp.length,
        width=inp.width,
        height=inp.height,
    )
    return result


# ── Shipping Rate Calculator ──────────────────────────────────────────────────

@router.post("/ShippingEstimate")
async def get_shipping_estimate(
    inp: ShippingEstimateInput,
    db: Session = Depends(get_db),
):
    """
    Get estimated shipping charges for a shipment.
    Useful for showing shipping costs at checkout.
    """
    client = get_ekart_client_for_db(db)
    result = await client.get_shipping_estimate(
        pickup_pincode=inp.pickup_pincode,
        drop_pincode=inp.drop_pincode,
        weight=inp.weight,
        payment_mode=inp.payment_mode,
        cod_amount=inp.cod_amount,
    )
    return result


# ── Set Dispatch Date ─────────────────────────────────────────────────────────

@router.post("/SetDispatchDate")
async def set_dispatch_date(
    inp: DispatchDateInput,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Set preferred pickup/dispatch date for delayed-dispatch shipments.
    dispatch_date format: YYYY-MM-DD
    """
    if not inp.awb_numbers:
        raise HTTPException(400, "No AWB numbers provided")

    client = get_ekart_client_for_db(db)
    result = await client.set_dispatch_date(inp.awb_numbers, inp.dispatch_date)
    return result


# ── COD Collection Report ─────────────────────────────────────────────────────

@router.get("/CODReport")
def get_cod_report(
    start_date: Optional[str] = None,  # YYYY-MM-DD
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    COD (Cash on Delivery) collection report.
    Shows delivered COD orders with amounts, from our DB + Ekart tracking data.
    """
    date_filter = ""
    params: dict = {}

    if start_date:
        date_filter += ' AND o."DeliveredDate" >= :start_date'
        params["start_date"] = start_date
    if end_date:
        date_filter += ' AND o."DeliveredDate" <= :end_date'
        params["end_date"] = end_date

    rows = db.execute(text(f"""
        SELECT
            o."OrderId",
            o."OrderNumber",
            o."TrackingId",
            o."TotalAmount",
            o."PaymentMethod",
            o."DeliveredDate",
            o."State",
            a."Name" AS customer_name,
            a."Phone" AS customer_phone,
            a."City"
        FROM twam."Orders" o
        LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
        WHERE o."PaymentMethod" = 'COD'
          AND o."State" = 'Delivered'
          AND o."DeletedInd" = false
          {date_filter}
        ORDER BY o."DeliveredDate" DESC
        LIMIT 500
    """), params).fetchall()

    items = [
        {
            "orderId":       r[0],
            "orderNumber":   r[1],
            "trackingId":    r[2],
            "codAmount":     float(r[3]) if r[3] else 0,
            "paymentMethod": r[4],
            "deliveredDate": r[5].isoformat() if r[5] else None,
            "state":         r[6],
            "customerName":  r[7],
            "customerPhone": r[8],
            "city":          r[9],
        }
        for r in rows
    ]

    total_cod = sum(i["codAmount"] for i in items)

    return {
        "count":       len(items),
        "totalCOD":    total_cod,
        "currency":    "INR",
        "startDate":   start_date,
        "endDate":     end_date,
        "orders":      items,
    }


# ── Admin: ShipmentConfigurations CRUD ───────────────────────────────────────

@router.get("/Config")
def get_shipment_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """View current shipping config from DB (password masked)."""
    from app.shipment.config_model import ShipmentConfigurations
    rows = db.query(ShipmentConfigurations).filter(
        ShipmentConfigurations.deletedInd == False
    ).all()

    return [
        {
            "id":              r.shipmentConfigurationId,
            "clientId":        r.clientId,
            "deliveryAgent":   r.deliveryAgent,
            "stateId":         r.stateId,
            "accessTokenURL":  r.accessTokenURL,
            "createShipmentURL": r.createShipmentURL,
            "cancelShipmentURL": r.cancelShipmentURL,
            "trackShipmentURL":  r.trackShipmentURL,
            "wayBillURL":      r.wayBillURL,
            "userName":        r.userName,
            "password":        "***" if r.password else None,
            "returnName":      r.returnName,
            "returnPhone":     r.returnPhone,
            "returnAddressLine1": r.returnAddressLine1,
            "returnAddressLine2": r.returnAddressLine2,
            "returnCity":      r.returnCity,
            "returnState":     r.returnState,
            "returnPinCode":   r.returnPinCode,
            "returnCountry":   r.returnCountry,
        }
        for r in rows
    ]


@router.put("/Config/{config_id}")
def update_shipment_config(
    config_id: int,
    payload: ShipmentConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """Update Ekart credentials and warehouse return address in DB."""
    from app.shipment.config_model import ShipmentConfigurations
    row = db.query(ShipmentConfigurations).filter(
        ShipmentConfigurations.shipmentConfigurationId == config_id,
        ShipmentConfigurations.deletedInd == False,
    ).first()
    if not row:
        raise HTTPException(404, "Config not found")

    update_map = payload.dict(exclude_none=True)
    for field, value in update_map.items():
        attr = field[0].lower() + field[1:]
        if hasattr(row, attr):
            setattr(row, attr, value)

    row.modifiedDate = datetime.now(timezone.utc)
    db.commit()

    # Bust token cache so next call re-authenticates with new credentials
    from app.ekart.client import _token_cache
    _token_cache.pop(row.clientId, None)

    return {"success": True, "message": "Shipment config updated"}


# ── Readiness Check ───────────────────────────────────────────────────────────

@router.get("/Readiness")
async def ekart_readiness(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    Check whether the Ekart integration is fully configured.
    Also checks SMS and SMTP configuration.
    """
    from app.shipment.config_model import ShipmentConfigurations
    from sqlalchemy import text

    row = db.query(ShipmentConfigurations).filter(
        ShipmentConfigurations.deliveryAgent.ilike("EKart%"),
        ShipmentConfigurations.deletedInd == False,
        ShipmentConfigurations.stateId == "Active",
    ).first()

    if not row:
        return {
            "ready_for_live": False,
            "mock_mode": True,
            "missing_required": ["No active EKart config in ShipmentConfigurations — run ekart_setup.sql"],
        }

    # Check Ekart config completeness
    ekart_missing = []
    if not row.accessTokenURL:    ekart_missing.append("AccessTokenURL")
    if not row.createShipmentURL: ekart_missing.append("CreateShipmentURL")
    if not row.cancelShipmentURL: ekart_missing.append("CancelShipmentURL")
    if not row.trackShipmentURL:  ekart_missing.append("TrackShipmentURL")
    if not row.userName:           ekart_missing.append("UserName")
    if not row.password:           ekart_missing.append("Password")
    if not row.returnAddressLine1: ekart_missing.append("ReturnAddressLine1")
    if not row.returnCity:         ekart_missing.append("ReturnCity")
    if not row.returnPinCode:      ekart_missing.append("ReturnPinCode")
    if not row.returnPhone:        ekart_missing.append("ReturnPhone")

    # Check SMS config
    sms_settings = {}
    try:
        sms_rows = db.execute(text(
            'SELECT "Key","Value" FROM twam."AppSettings" WHERE "Key" ILIKE \'SMS_%\' AND "DeletedInd"=false'
        )).fetchall()
        sms_settings = {r[0]: r[1] for r in sms_rows}
    except Exception:
        pass

    sms_missing = []
    if not sms_settings.get("SMS_API_URL") or "YOUR_SMS_DOMAIN" in (sms_settings.get("SMS_API_URL") or ""):
        sms_missing.append("SMS_API_URL")
    if not sms_settings.get("SMS_API_USERNAME") or sms_settings.get("SMS_API_USERNAME") == "YOUR_SMS_USERNAME":
        sms_missing.append("SMS_API_USERNAME")
    if not sms_settings.get("SMS_API_PASSWORD") or sms_settings.get("SMS_API_PASSWORD") == "YOUR_SMS_PASSWORD":
        sms_missing.append("SMS_API_PASSWORD")

    client = get_ekart_client_for_db(db)

    return {
        "ready_for_live":  len(ekart_missing) == 0 and not client.mock_mode,
        "mock_mode":       client.mock_mode,
        "ekart": {
            "missing": ekart_missing,
            "configured": {
                "auth":           bool(row.accessTokenURL),
                "create":         bool(row.createShipmentURL),
                "credentials":    bool(row.userName and row.password),
                "return_address": bool(row.returnAddressLine1 and row.returnPinCode),
            },
        },
        "sms": {
            "missing":    sms_missing,
            "configured": len(sms_missing) == 0,
        },
    }