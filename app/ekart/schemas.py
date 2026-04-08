"""
Ekart Schemas
─────────────
Pydantic models for Ekart API requests and responses.
These map to Ekart's actual API contract (spec.yaml).
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ── Configuration ─────────────────────────────────────────────────────────────

class EkartConfig(BaseModel):
    """Ekart API configuration — loaded from shipment.ShipmentConfigurations."""
    base_url: str = Field(default="https://app.elite.ekartlogistics.in")
    api_key: str = Field(default="")
    api_secret: str = Field(default="")
    seller_id: str = Field(default="")
    pickup_location_id: str = Field(default="")
    return_location_id: str = Field(default="")


# ── Address Models ────────────────────────────────────────────────────────────

class EkartAddress(BaseModel):
    """Address format for Ekart API."""
    name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"


# ── Shipment Request Models ───────────────────────────────────────────────────

class EkartShipmentItem(BaseModel):
    """Individual item in shipment."""
    name: str
    sku: Optional[str] = None
    quantity: int = 1
    price: float
    hsn_code: Optional[str] = None


class CreateShipmentRequest(BaseModel):
    """Request to create a forward shipment via Ekart."""
    order_id: int
    order_number: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None

    # Consignee (recipient) details
    consignee_name: str
    consignee_phone: str
    consignee_address: EkartAddress

    # Shipment details
    payment_mode: str = Field(default="Prepaid", description="Prepaid or COD")
    cod_amount: Optional[float] = None
    total_amount: float

    # Package details
    weight: float = Field(default=500, description="Weight in grams")
    length: Optional[int] = Field(default=20, description="Length in CM")
    width: Optional[int] = Field(default=15, description="Width in CM")
    height: Optional[int] = Field(default=10, description="Height in CM")

    # Items
    items: List[EkartShipmentItem] = []
    product_description: Optional[str] = None

    # GST details
    seller_gst: Optional[str] = None
    consignee_gst: Optional[str] = None
    tax_value: Optional[float] = None
    taxable_amount: Optional[float] = None


class CreateReturnShipmentRequest(BaseModel):
    """Request to create a return/reverse shipment."""
    order_id: int
    original_awb: str
    return_reason: str

    pickup_name: str
    pickup_phone: str
    pickup_address: EkartAddress

    return_address: EkartAddress

    weight: float = Field(default=500)
    items: List[EkartShipmentItem] = []


# ── Shipment Response Models ──────────────────────────────────────────────────

class EkartShipmentResponse(BaseModel):
    """Response from Ekart after creating shipment."""
    success: bool
    awb_number: Optional[str] = None
    tracking_url: Optional[str] = None
    courier_name: str = "Ekart"
    estimated_delivery: Optional[datetime] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


# ── Tracking Models ───────────────────────────────────────────────────────────

class EkartTrackingEvent(BaseModel):
    """Single tracking event from Ekart."""
    status: str
    status_code: str
    location: Optional[str] = None
    timestamp: datetime
    remarks: Optional[str] = None


class EkartTrackingResponse(BaseModel):
    """Full tracking response from Ekart."""
    awb_number: str
    current_status: str
    current_status_code: str
    expected_delivery: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    events: List[EkartTrackingEvent] = []


# ── Webhook Models ────────────────────────────────────────────────────────────
# These match the actual Ekart track_updated webhook payload from spec.yaml:
#
#   {
#     "ctime": 1657523187604,        ← ms-epoch timestamp
#     "status": "Delivered",         ← human-readable status string
#     "location": "",
#     "desc": "Delivered Successfully",
#     "attempts": "0",
#     "pickupTime": 1655980197000,
#     "wbn": "318019134877",         ← waybill / tracking ID
#     "id": "501346BN6838925",       ← Ekart internal ID
#     "orderNumber": "41839",        ← your order number
#     "edd": 1657523187609
#   }

class EkartWebhookPayload(BaseModel):
    """
    Payload received from Ekart track_updated webhook callbacks.

    Field aliases exactly match what Ekart sends (spec.yaml, Webhook V2 section).
    """
    # wbn = waybill number = our TrackingId stored in Orders
    awb_number: str = Field(alias="wbn")

    # orderNumber = the order number we sent when creating the shipment
    order_number: Optional[str] = Field(default=None, alias="orderNumber")

    # Ekart's internal tracking id (different from wbn)
    ekart_id: Optional[str] = Field(default=None, alias="id")

    # Human-readable status string — see EKART_STATUS_TEXT_TO_ORDER below
    status: str

    # Description of the status event
    desc: Optional[str] = Field(default=None)

    # Location of the scan
    location: Optional[str] = Field(default=None)

    # Timestamp of the event in milliseconds since Unix epoch
    ctime: Optional[int] = Field(default=None)

    # Pickup timestamp in milliseconds
    pickupTime: Optional[int] = Field(default=None)

    # Number of delivery attempts
    attempts: Optional[str] = Field(default=None)

    # Estimated delivery date timestamp
    edd: Optional[int] = Field(default=None)

    # Proof of delivery image URL (added by some Ekart implementations)
    pod_image_url: Optional[str] = Field(default=None)

    class Config:
        populate_by_name = True

    @property
    def status_datetime(self) -> Optional[datetime]:
        """Convert ctime (ms epoch) to datetime with UTC timezone."""
        if self.ctime:
            return datetime.fromtimestamp(self.ctime / 1000, tz=timezone.utc)
        return None

    @property
    def pickup_datetime(self) -> Optional[datetime]:
        if self.pickupTime:
            return datetime.fromtimestamp(self.pickupTime / 1000, tz=timezone.utc)
        return None


# ── Status Mappings ───────────────────────────────────────────────────────────

# Map Ekart human-readable webhook status strings → our order States
# Source: spec.yaml swift_status enum + actual webhook responses
EKART_STATUS_TEXT_TO_ORDER: dict[str, str] = {
    "Order Placed":           "Pending",
    "Picked Up":              "Processing",
    "In Transit":             "Shipped",
    "Out for Delivery":       "Out for Delivery",
    "Delivered":              "Delivered",
    "Delivery Rescheduled":   "Shipped",
    "Undelivered":            "Shipped",
    "Shipment Delayed":       "Shipped",
    "Not Picked":             "Processing",
    "Out for Pickup":         "Processing",
    "Pickup Scheduled":       "Processing",
    "Pickup Pending":         "Processing",
    "Pickup Cancelled":       "Cancelled",
    "Cancelled":              "Cancelled",
    "Seller Cancelled":       "Cancelled",
    "RTO Requested":          "Return Initiated",
    "Seller RTO Requested":   "Return Initiated",
    "RTO In Transit":         "Return Initiated",
    "RTO Out for Delivery":   "Return Initiated",
    "RTO Delivered":          "Returned",
    "RTO Failed":             "Return Initiated",
    "Not Serviceable":        "Shipped",
    "Lost":                   "Shipped",
    "Damaged":                "Shipped",
    "On Hold":                "Shipped",
}

# Keep the short-code mapping for any internal uses / manual status updates
EKART_TO_ORDER_STATUS: dict[str, str] = {
    "PKD": "Processing",
    "ITR": "Shipped",
    "OFD": "Out for Delivery",
    "DLV": "Delivered",
    "RTO": "Return Initiated",
    "RTD": "Returned",
    "CAN": "Cancelled",
    "UND": "Shipped",
    "HLD": "Shipped",
    "PNS": "Shipped",
    "NSL": "Shipped",
}

ORDER_STATE_TO_EKART: dict[str, list] = {
    "Pending":          ["NEW", "PND"],
    "Confirmed":        ["CNF", "RDY"],
    "Processing":       ["PKD", "HLD"],
    "Shipped":          ["ITR", "PNS", "UND"],
    "Out for Delivery": ["OFD"],
    "Delivered":        ["DLV"],
    "Return Initiated": ["RTO"],
    "Returned":         ["RTD"],
    "Cancelled":        ["CAN"],
}


# ── Cancel Shipment ───────────────────────────────────────────────────────────

class CancelShipmentRequest(BaseModel):
    awb_number: str
    reason: str = "Customer requested cancellation"


class CancelShipmentResponse(BaseModel):
    success: bool
    awb_number: str
    message: Optional[str] = None
    error_message: Optional[str] = None