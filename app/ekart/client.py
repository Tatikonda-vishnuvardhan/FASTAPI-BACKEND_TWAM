"""
app/ekart/client.py  — Ekart Elite Logistics API Client
========================================================
Covers every endpoint from the Ekart Elite API spec:

  Auth:              POST /integrations/v2/auth/token/{client_id}
  Create shipment:   PUT  /api/v1/package/create         (forward & reverse)
  Cancel shipment:   DELETE /api/v1/package/cancel?tracking_id=...
  Track (v1):        GET  /api/v1/track/{id}             (open, no auth)
  Track (elite):     GET  /data/v1/elite/track/{wbn}
  Label:             POST /api/v1/package/label
  Manifest:          POST /data/v2/generate/manifest
  NDR action:        POST /api/v2/package/ndr
  Serviceability v2: GET  /api/v2/serviceability/{pincode}
  Serviceability v3: POST /data/v3/serviceability
  Shipping estimate: POST /data/pricing/estimate
  Dispatch date:     POST /data/shipment/dispatch-date
  Bulk shipments:    multiple PUT /api/v1/package/create calls
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import httpx
except ModuleNotFoundError:
    httpx = None  # type: ignore

from .schemas import (
    EkartConfig,
    CreateShipmentRequest,
    CreateReturnShipmentRequest,
    EkartShipmentResponse,
    EkartTrackingResponse,
    EkartTrackingEvent,
    CancelShipmentRequest,
    CancelShipmentResponse,
    EKART_TO_ORDER_STATUS,
)

EKART_BASE_URL = "https://app.elite.ekartlogistics.in"

# ── Token cache (in-process, per client_id) ──────────────────────────────────
_token_cache: dict[str, dict] = {}
_TOKEN_BUFFER_SECS = 300  # refresh 5 min before expiry


def _cache_token(client_id: str, token: str, expires_in: int = 86400):
    _token_cache[client_id] = {
        "token": token,
        "expires_at": time.time() + expires_in - _TOKEN_BUFFER_SECS,
    }


def _get_cached_token(client_id: str) -> Optional[str]:
    entry = _token_cache.get(client_id)
    if entry and time.time() < entry["expires_at"]:
        return entry["token"]
    return None


# ── DB config loader ──────────────────────────────────────────────────────────

def load_ekart_config_from_db(db) -> Optional["EkartDbConfig"]:
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
        if not row:
            print("[EkartClient] No active EKart config found in DB — using mock mode")
            return None
        return EkartDbConfig(
            client_id=row.clientId or "",
            access_token_url=row.accessTokenURL or "",
            create_shipment_url=row.createShipmentURL or "",
            cancel_shipment_url=row.cancelShipmentURL or "",
            track_shipment_url=row.trackShipmentURL or "",
            waybill_url=row.wayBillURL or "",
            username=row.userName or "",
            password=row.password or "",
            return_name=row.returnName or "",
            return_phone=row.returnPhone or "",
            return_address_line1=row.returnAddressLine1 or "",
            return_address_line2=row.returnAddressLine2 or "",
            return_city=row.returnCity or "",
            return_state=row.returnState or "",
            return_pincode=row.returnPinCode or "",
            return_country=row.returnCountry or "India",
        )
    except Exception as e:
        print(f"[EkartClient] DB config load failed: {e}")
        return None


class EkartDbConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def is_complete(self) -> bool:
        return bool(
            self.access_token_url
            and self.create_shipment_url
            and self.username
            and self.password
        )


# ── Ekart Elite Client ────────────────────────────────────────────────────────

class EkartClient:
    def __init__(self, db_config: Optional[EkartDbConfig] = None):
        self.db_config = db_config
        self.mock_mode = (
            httpx is None
            or db_config is None
            or not db_config.is_complete
        )
        if self.mock_mode:
            reason = "httpx not installed" if httpx is None else (
                "no DB config" if db_config is None else "incomplete config"
            )
            print(f"[EkartClient] Running in MOCK mode ({reason})")

    # ── Authentication ────────────────────────────────────────────────────────
    # POST /integrations/v2/auth/token/{client_id}
    # Body: {"username": "...", "password": "..."}
    # Response: {"access_token": "...", "expires_in": N, "token_type": "Bearer"}

    async def _get_token(self) -> str:
        if self.mock_mode:
            return "mock-token"

        cfg = self.db_config
        cached = _get_cached_token(cfg.client_id)
        if cached:
            return cached

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                cfg.access_token_url,
                json={"username": cfg.username, "password": cfg.password},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        token = data.get("access_token") or data.get("token") or ""
        expires_in = int(data.get("expires_in", 86400))
        _cache_token(cfg.client_id, token, expires_in)
        print(f"[EkartClient] Got new token, expires in {expires_in}s")
        return token

    def _auth_headers(self, token: str) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    # ── Create Forward/Return Shipment ────────────────────────────────────────
    # PUT /api/v1/package/create
    # Response: {"status": true, "tracking_id": "...", "vendor": "...", "barcodes": {...}}

    async def create_shipment(self, request: CreateShipmentRequest) -> EkartShipmentResponse:
        if self.mock_mode:
            return self._mock_create_shipment(request)

        cfg = self.db_config
        try:
            token = await self._get_token()
            payload = self._build_create_payload(request)

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    cfg.create_shipment_url,
                    json=payload,
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                data = resp.json()

            success = data.get("status") is True
            awb = data.get("tracking_id") or data.get("awb_number") or data.get("awb")

            return EkartShipmentResponse(
                success=success,
                awb_number=str(awb) if awb else None,
                tracking_url=f"{EKART_BASE_URL}/track/{awb}" if awb else None,
                courier_name=data.get("vendor") or "Ekart",
                estimated_delivery=None,
                raw_response=data,
            )

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] create_shipment error: {err}")
            return EkartShipmentResponse(success=False, error_message=err)

    def _build_create_payload(self, req: CreateShipmentRequest) -> dict:
        """
        Build Ekart Elite v1 create-shipment payload.
        phone and pin MUST be integers. weight is in GRAMS.
        payment_mode: "COD" | "Prepaid" (case-sensitive)
        """
        cfg = self.db_config

        def _phone_int(phone: str) -> int:
            digits = "".join(c for c in (phone or "") if c.isdigit())
            return int(digits[-10:]) if len(digits) >= 10 else int(digits or "0")

        def _pin_int(pin: str) -> int:
            digits = "".join(c for c in (pin or "") if c.isdigit())
            return int(digits[:6]) if digits else 0

        ekart_payment_mode = "COD" if req.payment_mode == "COD" else "Prepaid"

        pickup_location = {
            "name":    cfg.return_name or "Warehouse",
            "phone":   _phone_int(cfg.return_phone),
            "address": cfg.return_address_line1 or "",
            "city":    cfg.return_city or "",
            "state":   cfg.return_state or "",
            "country": cfg.return_country or "India",
            "pin":     _pin_int(cfg.return_pincode),
        }

        addr = req.consignee_address
        drop_location = {
            "name":    addr.name or req.consignee_name,
            "phone":   _phone_int(addr.phone or req.consignee_phone),
            "address": addr.address_line1 + (f", {addr.address_line2}" if addr.address_line2 else ""),
            "city":    addr.city or "",
            "state":   addr.state or "",
            "country": addr.country or "India",
            "pin":     _pin_int(addr.pincode),
        }

        weight_grams = max(1, int((req.weight or 0.5) * 1000))

        return {
            "order_number":              req.order_number or str(req.order_id),
            "invoice_number":            req.invoice_number or req.order_number or str(req.order_id),
            "invoice_date":              req.invoice_date.strftime("%d-%m-%Y") if req.invoice_date else datetime.now().strftime("%d-%m-%Y"),
            "consignee_name":            req.consignee_name or addr.name,
            "consignee_alternate_phone": _phone_int(req.consignee_phone),
            "payment_mode":              ekart_payment_mode,
            "cod_amount":                float(req.cod_amount or 0) if ekart_payment_mode == "COD" else 0,
            "total_amount":              float(req.total_amount or 0),
            "tax_value":                 float(req.tax_value or 0),
            "taxable_amount":            float(req.taxable_amount or req.total_amount or 0),
            "commodity_value":           str(int(req.taxable_amount or req.total_amount or 0)),
            "consignee_gst_amount":      float(req.tax_value or 0),
            "seller_name":               cfg.return_name or "Seller",
            "seller_address":            cfg.return_address_line1 or "",
            "seller_gst_tin":            "",
            "products_desc":             req.product_description or "Fashion Apparel",
            "category_of_goods":         "Fashion",
            "hsn_code":                  ",".join(i.hsn_code for i in req.items if i.hsn_code) if req.items else "",
            "quantity":                  sum(i.quantity for i in req.items) if req.items else 1,
            "weight":                    weight_grams,
            "length":                    int(req.length or 30),
            "height":                    int(req.height or 5),
            "width":                     int(req.width or 25),
            "drop_location":             drop_location,
            "pickup_location":           pickup_location,
            "return_location":           pickup_location,
            "return_reason":             "",
        }

    # ── Bulk Shipment Creation ────────────────────────────────────────────────
    # Sends multiple concurrent PUT /api/v1/package/create requests.
    # Returns list of (order_id, EkartShipmentResponse).

    async def create_bulk_shipments(
        self, requests: list[CreateShipmentRequest]
    ) -> list[dict]:
        """
        Create multiple forward shipments concurrently (max 10 at once).
        Returns: [{"order_id": ..., "success": ..., "awb_number": ..., "error": ...}]
        """
        async def _one(req: CreateShipmentRequest) -> dict:
            result = await self.create_shipment(req)
            return {
                "order_id":   req.order_id,
                "order_number": req.order_number,
                "success":    result.success,
                "awb_number": result.awb_number,
                "tracking_url": result.tracking_url,
                "error":      result.error_message,
            }

        # Process in batches of 10 to avoid overwhelming the API
        results = []
        batch_size = 10
        for i in range(0, len(requests), batch_size):
            batch = requests[i : i + batch_size]
            batch_results = await asyncio.gather(*[_one(r) for r in batch])
            results.extend(batch_results)

        return results

    # ── Create Return Shipment ────────────────────────────────────────────────
    # payment_mode = "Pickup" for reverse shipments

    async def create_return_shipment(self, request: CreateReturnShipmentRequest) -> EkartShipmentResponse:
        if self.mock_mode:
            return self._mock_create_return_shipment(request)

        cfg = self.db_config

        def _phone_int(phone: str) -> int:
            digits = "".join(c for c in (phone or "") if c.isdigit())
            return int(digits[-10:]) if len(digits) >= 10 else int(digits or "0")

        def _pin_int(pin: str) -> int:
            digits = "".join(c for c in (pin or "") if c.isdigit())
            return int(digits[:6]) if digits else 0

        try:
            token = await self._get_token()
            pickup = request.pickup_address
            ret_addr = request.return_address

            payload = {
                "order_number":              str(request.order_id),
                "invoice_number":            str(request.order_id),
                "invoice_date":              datetime.now().strftime("%d-%m-%Y"),
                "consignee_name":            request.pickup_name,
                "consignee_alternate_phone": _phone_int(request.pickup_phone),
                "payment_mode":              "Pickup",
                "return_reason":             request.return_reason or "Customer return",
                "total_amount":              0,
                "tax_value":                 0,
                "taxable_amount":            0,
                "commodity_value":           "0",
                "consignee_gst_amount":      0,
                "cod_amount":                0,
                "seller_name":               ret_addr.name,
                "seller_address":            ret_addr.address_line1,
                "seller_gst_tin":            "",
                "products_desc":             "Return — Fashion Apparel",
                "category_of_goods":         "Fashion",
                "quantity":                  sum(i.quantity for i in request.items) if request.items else 1,
                "weight":                    500,
                "length":                    30,
                "height":                    5,
                "width":                     25,
                "drop_location": {
                    "name":    request.pickup_name,
                    "phone":   _phone_int(request.pickup_phone),
                    "address": pickup.address_line1,
                    "city":    pickup.city,
                    "state":   pickup.state,
                    "country": pickup.country or "India",
                    "pin":     _pin_int(pickup.pincode),
                },
                "pickup_location": {
                    "name":    ret_addr.name,
                    "phone":   _phone_int(ret_addr.phone),
                    "address": ret_addr.address_line1,
                    "city":    ret_addr.city,
                    "state":   ret_addr.state,
                    "country": ret_addr.country or "India",
                    "pin":     _pin_int(ret_addr.pincode),
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    cfg.create_shipment_url,
                    json=payload,
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                data = resp.json()

            awb = data.get("tracking_id") or data.get("awb")
            return EkartShipmentResponse(
                success=data.get("status") is True,
                awb_number=str(awb) if awb else None,
                tracking_url=f"{EKART_BASE_URL}/track/{awb}" if awb else None,
                courier_name="Ekart",
            )

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] create_return_shipment error: {err}")
            return EkartShipmentResponse(success=False, error_message=err)

    # ── Track Shipment (v1 — open API, no auth) ───────────────────────────────
    # GET /api/v1/track/{id}

    async def track_shipment(self, awb_number: str) -> EkartTrackingResponse:
        if self.mock_mode:
            return self._mock_track_shipment(awb_number)

        try:
            track_base = (
                self.db_config.track_shipment_url
                if self.db_config
                else f"{EKART_BASE_URL}/api/v1/track"
            )
            url = track_base.rstrip("/") + f"/{awb_number}"

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                data = resp.json()

            events = []
            track = data.get("track") or {}
            raw_history = data.get("history") or track.get("history") or []

            if awb_number in data:
                raw_data = data[awb_number]
                raw_history = raw_data.get("history") or []
                current_status = raw_data.get("status") or "Unknown"
            else:
                current_status = track.get("status") or data.get("status") or "In Transit"

            for evt in raw_history:
                ts_str = evt.get("event_date_iso8601") or evt.get("event_date") or evt.get("timestamp")
                try:
                    ts = datetime.fromisoformat(ts_str.replace("+0530", "+05:30")) if ts_str else datetime.now(timezone.utc)
                except Exception:
                    ts = datetime.now(timezone.utc)

                events.append(EkartTrackingEvent(
                    status=evt.get("public_description") or evt.get("status") or "",
                    status_code=evt.get("status") or "UNK",
                    location=evt.get("city") or evt.get("hub_name") or "",
                    timestamp=ts,
                    remarks=evt.get("hub_notes") or evt.get("cs_notes") or "",
                ))

            return EkartTrackingResponse(
                awb_number=awb_number,
                current_status=current_status,
                current_status_code=current_status.upper().replace(" ", "_")[:10],
                expected_delivery=None,
                delivered_date=None,
                events=events,
            )

        except Exception as e:
            print(f"[EkartClient] track_shipment error: {e}")
            return EkartTrackingResponse(
                awb_number=awb_number,
                current_status="Tracking Unavailable",
                current_status_code="ERR",
                events=[],
            )

    # ── Track (Elite raw API) ─────────────────────────────────────────────────
    # GET /data/v1/elite/track/{wbn}  — returns full raw Ekart response

    async def track_shipment_elite(self, wbn: str) -> dict:
        if self.mock_mode:
            return {"mock": True, "wbn": wbn, "status": "In Transit"}

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/data/v1/elite/track/{wbn}"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=self._auth_headers(token))
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {"error": str(e), "wbn": wbn}

    # ── Cancel Shipment ───────────────────────────────────────────────────────
    # DELETE /api/v1/package/cancel?tracking_id={id}

    async def cancel_shipment(self, request: CancelShipmentRequest) -> CancelShipmentResponse:
        if self.mock_mode:
            return CancelShipmentResponse(
                success=True, awb_number=request.awb_number,
                message="Cancelled (mock mode)",
            )

        cfg = self.db_config
        try:
            token = await self._get_token()

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.delete(
                    cfg.cancel_shipment_url,
                    params={"tracking_id": request.awb_number},
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()

            return CancelShipmentResponse(
                success=True,
                awb_number=request.awb_number,
                message="Shipment cancelled on Ekart",
            )

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] cancel_shipment error: {err}")
            return CancelShipmentResponse(
                success=False, awb_number=request.awb_number, error_message=err,
            )

    # ── Download Label ────────────────────────────────────────────────────────
    # POST /api/v1/package/label
    # Body: {"ids": ["awb1", "awb2", ...]}
    # Returns: PDF binary (or JSON if json_only=true)

    async def download_label(
        self, awb_numbers: list[str], json_only: bool = False
    ) -> bytes | dict:
        if self.mock_mode:
            return {"mock": True, "message": "Label would be returned as PDF bytes"}

        cfg = self.db_config
        try:
            token = await self._get_token()
            url = cfg.waybill_url or f"{EKART_BASE_URL}/api/v1/package/label"
            params = {"json_only": "true"} if json_only else {}

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json={"ids": awb_numbers},
                    headers=self._auth_headers(token),
                    params=params,
                )
                resp.raise_for_status()

            if json_only:
                return resp.json()
            return resp.content  # raw PDF bytes

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] download_label error: {err}")
            return {"error": err}

    # ── Download Manifest ─────────────────────────────────────────────────────
    # POST /data/v2/generate/manifest
    # Body: {"ids": ["awb1", "awb2", ...]}
    # Returns: JSON with manifest data

    async def download_manifest(self, awb_numbers: list[str]) -> dict:
        if self.mock_mode:
            return {
                "mock": True,
                "manifest_id": "MOCK-MANIFEST-001",
                "count": len(awb_numbers),
                "awb_numbers": awb_numbers,
            }

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/data/v2/generate/manifest"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url,
                    json={"ids": awb_numbers},
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] download_manifest error: {err}")
            return {"error": err}

    # ── NDR Action ────────────────────────────────────────────────────────────
    # POST /api/v2/package/ndr
    # NDR = Non-Delivery Report
    # ndrAction values: "RE_ATTEMPT", "RTO", "CONFIRM_DELIVERY"

    async def action_ndr(
        self,
        tracking_id: str,
        ndr_action: str,
        remarks: str = "",
        preferred_date: Optional[str] = None,
    ) -> dict:
        """
        Take action on a Non-Delivery Report shipment.
        ndr_action: "RE_ATTEMPT" | "RTO" | "CONFIRM_DELIVERY"
        preferred_date: "YYYY-MM-DD" for RE_ATTEMPT scheduling (optional)
        """
        if self.mock_mode:
            return {"mock": True, "tracking_id": tracking_id, "action": ndr_action}

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/api/v2/package/ndr"

            payload: dict = {
                "tracking_id": tracking_id,
                "ndrAction":   ndr_action,
                "remarks":     remarks,
            }
            if preferred_date:
                payload["preferredDate"] = preferred_date

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] action_ndr error: {err}")
            return {"error": err, "tracking_id": tracking_id}

    # ── Serviceability V2 ─────────────────────────────────────────────────────
    # GET /api/v2/serviceability/{pincode}
    # Returns: COD availability, forward/reverse serviceability

    async def check_serviceability_v2(self, pincode: str) -> dict:
        if self.mock_mode:
            return {
                "mock": True,
                "pincode": pincode,
                "cod": True,
                "forward_serviceable": True,
                "reverse_serviceable": True,
            }

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/api/v2/serviceability/{pincode}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._auth_headers(token))
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            print(f"[EkartClient] serviceability_v2 error: {e}")
            return {"error": str(e), "pincode": pincode}

    # ── Serviceability V3 ─────────────────────────────────────────────────────
    # POST /data/v3/serviceability
    # Returns: list of available courier partners for pickup→drop pincodes

    async def check_serviceability_v3(
        self,
        pickup_pincode: str,
        drop_pincode: str,
        weight: float = 0.5,
        length: float = 30,
        width: float = 25,
        height: float = 5,
    ) -> list:
        if self.mock_mode:
            return [{
                "mock": True,
                "pickup_pincode": pickup_pincode,
                "drop_pincode": drop_pincode,
                "courier": "Ekart",
                "cod_available": True,
                "estimated_days": 3,
            }]

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/data/v3/serviceability"
            weight_grams = max(1, int(weight * 1000))

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "pickupPincode": pickup_pincode,
                        "dropPincode":   drop_pincode,
                        "length":        str(int(length)),
                        "width":         str(int(width)),
                        "height":        str(int(height)),
                        "weight":        weight_grams,
                    },
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            print(f"[EkartClient] serviceability_v3 error: {e}")
            return [{"error": str(e)}]

    # ── Shipping Rate Estimate ────────────────────────────────────────────────
    # POST /data/pricing/estimate
    # Returns: estimated shipping rates / charges

    async def get_shipping_estimate(
        self,
        pickup_pincode: str,
        drop_pincode: str,
        weight: float = 0.5,
        payment_mode: str = "Prepaid",
        cod_amount: float = 0,
    ) -> dict:
        if self.mock_mode:
            # Sensible mock: flat ₹60 prepaid, ₹80 COD
            charge = 80.0 if payment_mode == "COD" else 60.0
            return {
                "mock": True,
                "pickup_pincode": pickup_pincode,
                "drop_pincode": drop_pincode,
                "estimated_charge": charge,
                "currency": "INR",
                "estimated_days": 3,
                "vendor": "Ekart",
            }

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/data/pricing/estimate"
            weight_grams = max(1, int(weight * 1000))

            payload = {
                "pickup_pincode": pickup_pincode,
                "drop_pincode":   drop_pincode,
                "weight":         weight_grams,
                "payment_mode":   payment_mode,
                "cod_amount":     cod_amount if payment_mode == "COD" else 0,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            print(f"[EkartClient] get_shipping_estimate error: {e}")
            return {"error": str(e)}

    # ── Set Dispatch Date ─────────────────────────────────────────────────────
    # POST /data/shipment/dispatch-date
    # For delayed_dispatch=true shipments — set preferred pickup date

    async def set_dispatch_date(self, awb_numbers: list[str], dispatch_date: str) -> dict:
        """
        dispatch_date: "YYYY-MM-DD" format
        """
        if self.mock_mode:
            return {"mock": True, "ids": awb_numbers, "dispatchDate": dispatch_date}

        try:
            token = await self._get_token()
            url = f"{EKART_BASE_URL}/data/shipment/dispatch-date"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={"ids": awb_numbers, "dispatchDate": dispatch_date},
                    headers=self._auth_headers(token),
                )
                resp.raise_for_status()
                return resp.json()

        except Exception as e:
            err = self._extract_error(e)
            print(f"[EkartClient] set_dispatch_date error: {err}")
            return {"error": err}

    # ── COD Collection Report ─────────────────────────────────────────────────
    # GET /data/v1/elite/track/{wbn} → filter delivered COD shipments
    # Ekart does not expose a dedicated COD report endpoint; we build it from
    # our local DB + live track calls.

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_error(e: Exception) -> str:
        if httpx and isinstance(e, httpx.HTTPStatusError):
            try:
                body = e.response.json()
                return body.get("message") or body.get("description") or str(e)
            except Exception:
                return f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        return str(e)

    # ── Mock Responses ────────────────────────────────────────────────────────

    def _mock_create_shipment(self, req: CreateShipmentRequest) -> EkartShipmentResponse:
        import random
        awb = f"500999{random.randint(1000000, 9999999)}"
        return EkartShipmentResponse(
            success=True,
            awb_number=awb,
            tracking_url=f"{EKART_BASE_URL}/track/{awb}",
            courier_name="Ekart (mock)",
        )

    def _mock_create_return_shipment(self, req: CreateReturnShipmentRequest) -> EkartShipmentResponse:
        import random
        awb = f"500RTN{random.randint(1000000, 9999999)}"
        return EkartShipmentResponse(success=True, awb_number=awb, courier_name="Ekart (mock)")

    def _mock_track_shipment(self, awb: str) -> EkartTrackingResponse:
        now = datetime.now(timezone.utc)
        return EkartTrackingResponse(
            awb_number=awb,
            current_status="In Transit",
            current_status_code="ITR",
            expected_delivery=now,
            events=[
                EkartTrackingEvent(
                    status="Picked Up from Seller",
                    status_code="PKD",
                    location="Hyderabad Hub",
                    timestamp=now,
                    remarks="Package picked up",
                ),
                EkartTrackingEvent(
                    status="In Transit",
                    status_code="ITR",
                    location="Hyderabad Hub",
                    timestamp=now,
                    remarks="Package moving to destination",
                ),
            ],
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def get_ekart_client_for_db(db) -> EkartClient:
    db_config = load_ekart_config_from_db(db)
    return EkartClient(db_config=db_config)


def map_ekart_status_to_order_state(ekart_status: str) -> str:
    return EKART_TO_ORDER_STATUS.get(ekart_status, "Shipped")


# ── Legacy singleton ──────────────────────────────────────────────────────────
_legacy_client: Optional[EkartClient] = None


def get_ekart_client() -> EkartClient:
    global _legacy_client
    if _legacy_client is None:
        _legacy_client = EkartClient(db_config=None)
    return _legacy_client
