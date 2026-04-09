"""
app/payment/payg_client.py
──────────────────────────
PayG payment gateway API client.

All credentials are fetched from AppSettings (DB) at call-time so they
can be updated through the admin panel without restarting the server.
Zero hardcoded secrets in this file.

PayG integration flow:
  1. call create_payg_order()  → returns ProcessingUrl
  2. redirect user's browser to ProcessingUrl
  3. user pays on PayG-hosted page
  4. PayG redirects browser to our RedirectUrl (GET or POST)
  5. /api/Payment/Callback verifies hash, updates order, redirects to frontend

PayG response codes (PaymentResponseCode):
  0 – Initiated / pending
  1 – Approved  ✓
  2 – Declined  ✗
  4 – Pending (awaiting bank confirmation)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime
from typing import Optional

import httpx


# ── API base URLs ──────────────────────────────────────────────────────────

_UAT_CREATE_URL  = "https://uatapiv2.payg.in/payment/api/order/create"
_LIVE_CREATE_URL = "https://apiv2.payg.in/payment/api/order/create"
_UAT_DETAIL_URL  = "https://uatapiv2.payg.in/payment/api/order/Detail"
_LIVE_DETAIL_URL = "https://apiv2.payg.in/payment/api/order/Detail"


# ── Credential helpers ─────────────────────────────────────────────────────

def _cfg(key: str, default: str = "") -> str:
    """Read a setting from the in-process AppSettings cache."""
    from app.shared.app_settings import get_setting
    return get_setting(key, default)


def _get_create_url() -> str:
    return _LIVE_CREATE_URL if _cfg("payg_mode", "uat").lower() == "live" else _UAT_CREATE_URL


def _get_detail_url() -> str:
    return _LIVE_DETAIL_URL if _cfg("payg_mode", "uat").lower() == "live" else _UAT_DETAIL_URL


def _sanitize_phone(phone) -> str:
    """
    PayG requires exactly a 10-digit Indian mobile number (no +91, no spaces).

    FIX: Handles all messy inputs:
      - None / empty string  → falls back to merchant support phone
      - Accidental tuple     → unwraps first element (trailing-comma bug in repository)
      - "+91 7036534449"     → "7036534449"
      - "91 9876543210"      → "9876543210"
      - "07036534449"        → "7036534449"
      - Already clean 10-dig → returned as-is
    """
    # Unwrap accidental tuple from repository trailing-comma bug
    if isinstance(phone, (tuple, list)):
        phone = phone[0] if phone else ""

    p = re.sub(r"[^\d]", "", str(phone or ""))   # strip everything except digits

    if p.startswith("91") and len(p) == 12:       # strip STD +91
        p = p[2:]
    if p.startswith("0") and len(p) == 11:        # strip leading 0
        p = p[1:]

    print(f"[PayG] _sanitize_phone({phone!r}) → '{p}'")

    if len(p) == 10 and p[0] in "6789":
        return p

    # Fallback: use SUPPORT_PHONE from AppSettings (a real registered number)
    support = re.sub(r"[^\d]", "", _cfg("SUPPORT_PHONE", "7036534449"))
    if support.startswith("91") and len(support) == 12:
        support = support[2:]
    if len(support) == 10 and support[0] in "6789":
        print(f"[PayG] Phone fallback to support phone: '{support}'")
        return support

    return "7036534449"   # absolute last resort — the merchant support number


def _build_auth_header() -> str:
    """
    PayG requires:  Authorization: Basic base64(AuthKey:AuthToken:M:MerchantKeyId)

    BUG FIX: The format is AuthKey:AuthToken:M:MerchantKeyId — NOT just AuthKey:AuthToken.
    PayG docs confirm: decode their example YjYwYmU... → "b60be...:84628...:M:8792"
    Omitting ':M:MerchantKeyId' causes PayG to reject ALL requests with an auth error.
    """
    auth_key        = _cfg("payg_auth_key")
    auth_token      = _cfg("payg_auth_token")
    merchant_key_id = _cfg("payg_merchant_key_id", "0")
    raw             = f"{auth_key}:{auth_token}:M:{merchant_key_id}"
    encoded         = base64.b64encode(raw.encode()).decode()
    return f"Basic {encoded}"


# ── Hash computation ───────────────────────────────────────────────────────

def compute_hash(mid: str, unique_request_id: str, order_amount: str) -> str:
    """
    PayG hash = HMAC-SHA256(SecureHashKey, "MID|UniqueRequestId|OrderAmount")
    Returns uppercase hex string.

    BUG FIX: order_amount must always have exactly 2 decimal places ("100.50"
    not "100.5"). Use f"{float(amount):.2f}" when calling this function.
    """
    secret  = _cfg("payg_secure_hash", "")
    message = f"{mid}|{unique_request_id}|{order_amount}"
    sig = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()
    return sig


def verify_callback_hash(response_data: dict) -> bool:
    """
    Verify that the PayG callback payload was signed by PayG using our
    SecureHashKey.  Returns False if the HashData field is missing or wrong.
    In UAT dev mode an empty hash is treated as 'no verification' by the
    caller — this function still validates mathematically if a hash is present.
    """
    received_hash = response_data.get("HashData", "")
    if not received_hash:
        return False
    mid           = response_data.get("MID", "")
    unique_req_id = response_data.get("UniqueRequestId", "")
    order_amount  = str(response_data.get("OrderAmount", ""))
    expected = compute_hash(mid, unique_req_id, order_amount)
    return hmac.compare_digest(expected, received_hash.upper())


# ── Order creation ─────────────────────────────────────────────────────────

def create_payg_order(
    *,
    order_id: int,
    order_number: str,
    amount: float,
    customer_name: str,
    customer_email: str,
    customer_phone,          # str | tuple | None — sanitized internally
    billing_address: str,
    billing_city: str,
    billing_state: str,
    billing_zip: str,
    redirect_url: str,
) -> dict:
    """
    Call PayG /payment/api/order/create and return the full response dict.
    On success the dict contains 'ProcessingUrl' — redirect the user there.
    Also includes '_unique_request_id' for tracking.
    Raises RuntimeError on HTTP or PayG-level failure.
    """
    mid               = _cfg("payg_mid")
    unique_request_id = f"ORD{order_id}-{uuid.uuid4().hex[:8].upper()}"

    # BUG FIX: Always format amount to exactly 2 decimal places.
    # str(round(100.5, 2)) → '100.5' which breaks the HMAC hash verification.
    # f"{100.5:.2f}" → '100.50' which matches what PayG expects.
    amount_str  = f"{float(amount):.2f}"
    now_str     = datetime.now().strftime("%m%d%Y")   # MMDDYYYY
    hash_data   = compute_hash(mid, unique_request_id, amount_str)
    clean_phone = _sanitize_phone(customer_phone)

    first, *rest = (customer_name or "Customer").split(" ", 1)
    last = rest[0] if rest else ""

    # ProductData MUST be a JSON string, not a dict object.
    product_data_str = f"{{'PaymentReason': 'Order {order_number}'}}"

    # ── FIX: PayG UAT does not append params to RedirectUrl on browser redirect.
    # Embed order_id (oid) and unique_request_id (rid) into the redirect URL
    # so the callback can always identify the order and call the Detail API.
    sep = "&" if "?" in redirect_url else "?"
    redirect_url_with_ids = f"{redirect_url}{sep}oid={order_id}&rid={unique_request_id}"

    payload = {
        "MID": mid,
        "UniqueRequestId": unique_request_id,
        "UserDefinedData": {
            "UserDefined1": str(order_id),
        },
        "ProductData": product_data_str,
        "RequestDateTime": now_str,
        "RedirectUrl": redirect_url_with_ids,
        "TransactionData": {
            "AcceptedPaymentTypes": "",
            "PaymentType": "",
            "SurchargeType": "",
            "SurchargeValue": "",
            "RefTransactionId": "",
            "IndustrySpecificationCode": "",
            "PartialPaymentOption": "",
        },
        "OrderAmount": amount_str,
        "OrderType": "",
        "OrderAmountData": {
            "AmountTypeDesc": "3",
            "Amount": amount_str,
        },
        "CustomerData": {
            "CustomerId": str(order_id),
            "CustomerNotes": f"Order {order_number}",
            "FirstName": first,
            "LastName": last,
            "MobileNo": clean_phone,
            "Email": customer_email or "",
            "EmailReceipt": "true",
            "BillingAddress": billing_address or "",
            "BillingCity": billing_city or "",
            "BillingState": billing_state or "",
            "BillingCountry": "India",
            "BillingZipCode": billing_zip or "",
            "ShippingFirstName": first,
            "ShippingLastName": last,
            "ShippingAddress": billing_address or "",
            "ShippingCity": billing_city or "",
            "ShippingState": billing_state or "",
            "ShippingCountry": "India",
            "ShippingZipCode": billing_zip or "",
            "ShippingMobileNo": clean_phone,
        },
        "IntegrationData": {
            "UserName": first,
            "Source": "WebPortal",
            "IntegrationType": "",
            "HashData": hash_data,
            "PlatformId": "1",
        },
    }

    headers = {
        "Authorization": _build_auth_header(),
        "Content-Type": "application/json",
    }

    create_url = _get_create_url()
    print(f"[PayG] Calling {create_url}")
    print(f"[PayG] MID={mid}, MerchantKeyId={_cfg('payg_merchant_key_id')}, "
          f"Phone={clean_phone}, RedirectUrl={redirect_url}")

    try:
        resp = httpx.post(
            create_url,
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        print(f"[PayG] HTTP {resp.status_code} from {create_url}")
        print(f"[PayG] Response body: {resp.text[:1000]}")
        resp.raise_for_status()
        data = resp.json()
    except httpx.ConnectTimeout as exc:
        raise RuntimeError(
            "PayG gateway is unreachable (connect timeout). "
            "Possible causes:\n"
            "  1. Your network/ISP is blocking uatapiv2.payg.in — try a mobile hotspot.\n"
            "  2. PayG UAT server is temporarily down — check https://uat.payg.in\n"
            "  3. payg_redirect_url in AppSettings is still the placeholder — update it "
            "to your current ngrok URL, e.g. https://your-id.ngrok-free.dev/api/Payment/Callback"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PayG HTTP error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"PayG request failed: {exc}") from exc

    # Validate that PayG actually returned a payment URL.
    # PayG can return HTTP 200 with an error payload — we must detect this.
    processing_url = data.get("ProcessingUrl") or data.get("PaymentProcessUrl")
    if not processing_url:
        error_msg = (
            data.get("message")
            or data.get("Message")
            or data.get("error")
            or data.get("Error")
            or data.get("ResponseMessage")
            or data.get("responseMessage")
            or "No ProcessingUrl returned"
        )
        raise RuntimeError(
            f"PayG order creation failed — {error_msg}. "
            f"Full PayG response: {json.dumps(data)}"
        )

    data["_unique_request_id"] = unique_request_id
    return data


# ── Order status / detail ──────────────────────────────────────────────────

def get_payg_order_detail(
    order_key_id: Optional[str] = None,
    unique_request_id: Optional[str] = None,
    mid: Optional[str] = None,
) -> dict:
    """
    Fetch PayG /payment/api/order/Detail to get live payment status.
    Pass either order_key_id OR unique_request_id.

    PaymentResponseCode meanings:
      0 – Initiated
      1 – Approved  ✓
      2 – Declined  ✗
      4 – Pending
    """
    _mid = mid or _cfg("payg_mid")
    merchant_key_id = _cfg("payg_merchant_key_id", "0")

    body: dict = {
        "MID": _mid,
        "MerchantKeyId": int(merchant_key_id) if merchant_key_id.isdigit() else 0,
    }
    if order_key_id:
        body["OrderKeyId"] = order_key_id
    elif unique_request_id:
        body["UniqueRequestId"] = unique_request_id
    else:
        raise ValueError("Provide either order_key_id or unique_request_id")

    headers = {
        "Authorization": _build_auth_header(),
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(
            _get_detail_url(),
            json=body,
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PayG detail HTTP error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"PayG detail request failed: {exc}") from exc


# ── Response code → order state mapping ───────────────────────────────────

def payment_code_to_order_state(code: int) -> str:
    """Map PayG PaymentResponseCode to our internal order state string."""
    return {
        0: "Pending",
        1: "Confirmed",
        2: "Payment Failed",
        4: "Payment Pending",
    }.get(code, "Payment Failed")