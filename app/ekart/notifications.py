"""
app/ekart/notifications.py
───────────────────────────
SMS and email notifications for all order lifecycle events.

Configuration sources:
  SMS credentials (URL, username, password, sender ID, unicode flag)
      → twam.AppSettings (keys: SMS_API_URL, SMS_API_USERNAME, etc.)

  SMS template text + DLT Content ID
      → mdm.MessageTemplate (columns: messageType, messageContent, dltId)
      → messageType values: ORDER_PLACED, ORDER_SHIPPED, ORDER_OUT_FOR_DELIVERY,
                            ORDER_DELIVERED, ORDER_CANCELLED, RETURN_INITIATED

  Company name, support email, tracking URL
      → twam.AppSettings (COMPANY_NAME, SUPPORT_EMAIL, TRACKING_BASE_URL, etc.)

SMS API (HTTP GET):
  https://domain/fe/api/v1/send
  ?username=U&password=P&unicode=false&from=SENDER&to=NUMBER&text=MSG&dltContentId=ID

Template variable substitution:
  {order_number}   {company_name}   {tracking_id}   {total_amount}
  {customer_name}  {city}           {pincode}
"""

import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.sendemail.repository import send_email
from app.sendemail.schemas import EmailCreate


# ── AppSettings cache (5-minute TTL) ─────────────────────────────────────────

_settings_cache: dict = {}
_settings_ts: float = 0.0
_SETTINGS_TTL = 300


def _get_app_settings(db: Session) -> dict:
    global _settings_cache, _settings_ts
    if time.time() - _settings_ts < _SETTINGS_TTL and _settings_cache:
        return _settings_cache
    try:
        rows = db.execute(
            text('SELECT "Key","Value" FROM twam."AppSettings" WHERE "DeletedInd"=false')
        ).fetchall()
        _settings_cache = {r[0]: r[1] for r in rows}
        _settings_ts = time.time()
    except Exception as e:
        print(f"[Notifications] Could not load AppSettings: {e}")
        _settings_cache = {}
        _settings_ts = time.time()
    return _settings_cache


def _cfg(db: Session, key: str, fallback: str = "") -> str:
    return _get_app_settings(db).get(key) or fallback


# ── MessageTemplate cache (5-minute TTL) ─────────────────────────────────────
# Keyed by messageType string.  Holds {messageContent, dltId, templateId}.

_template_cache: dict = {}
_template_ts: float = 0.0
_TEMPLATE_TTL = 300


def _get_all_templates(db: Session) -> dict:
    """
    Returns dict of messageType → {messageContent, dltId, templateId}.
    Only returns rows where state='Active' and deletedInd=false.
    """
    global _template_cache, _template_ts
    if time.time() - _template_ts < _TEMPLATE_TTL and _template_cache:
        return _template_cache
    try:
        rows = db.execute(text("""
            SELECT "MessageType", "MessageContent", "DLTId", "TemplateId"
            FROM mdm."MessageTemplate"
            WHERE "DeletedInd" = false
              AND LOWER("State") = 'active'
        """)).fetchall()
        _template_cache = {
            r[0]: {
                "messageContent": r[1] or "",
                "dltId":          r[2] or "",
                "templateId":     r[3] or "",
            }
            for r in rows
            if r[0]  # skip rows with null messageType
        }
        _template_ts = time.time()
    except Exception as e:
        print(f"[Notifications] Could not load MessageTemplate: {e}")
        _template_cache = {}
        _template_ts = time.time()
    return _template_cache


def _get_template(db: Session, message_type: str) -> Optional[dict]:
    """
    Fetch a single template by messageType.
    Returns None if not found or not active.
    """
    return _get_all_templates(db).get(message_type)


def _render_template(content: str, variables: dict) -> str:
    """
    Simple {variable} substitution in template content.
    Missing variables are left as-is so partial templates still send.
    """
    for key, value in variables.items():
        content = content.replace(f"{{{key}}}", str(value) if value else "")
    return content


# MessageType constants — must match what is stored in mdm.MessageTemplate
MT_ORDER_PLACED          = "ORDER_PLACED"
MT_ORDER_SHIPPED         = "ORDER_SHIPPED"
MT_OUT_FOR_DELIVERY      = "ORDER_OUT_FOR_DELIVERY"
MT_ORDER_DELIVERED       = "ORDER_DELIVERED"
MT_ORDER_CANCELLED       = "ORDER_CANCELLED"
MT_RETURN_INITIATED      = "RETURN_INITIATED"


# ── Order details helpers ─────────────────────────────────────────────────────

def _get_order_details(db: Session, order_id: int) -> Optional[dict]:
    row = db.execute(text("""
        SELECT
            o."OrderId", o."OrderNumber", o."TotalAmount", o."State",
            o."TrackingId", o."IsWhatsappNotification", o."UserProfileId",
            o."DeliveredDate", o."DeliveryCharge",
            a."Name"       AS customer_name,
            a."Phone"      AS customer_phone,
            a."AddressLine" AS address_line,
            a."City"       AS city,
            a."PinCode"    AS pincode,
            p."Email"      AS customer_email
        FROM twam."Orders" o
        LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
        LEFT JOIN twam."People"  p ON p."UserProfileId" = o."UserProfileId"
        WHERE o."OrderId" = :order_id AND o."DeletedInd" = false
        LIMIT 1
    """), {"order_id": order_id}).fetchone()

    if not row:
        return None

    return {
        "order_id":          row[0],
        "order_number":      row[1] or str(row[0]),
        "total_amount":      float(row[2]) if row[2] else 0,
        "state":             row[3],
        "tracking_id":       row[4],
        "whatsapp_opted_in": row[5] or False,
        "user_profile_id":   row[6],
        "delivered_date":    row[7],
        "delivery_charge":   float(row[8]) if row[8] else 0,
        "customer_name":     row[9]  or "Valued Customer",
        "customer_phone":    row[10],
        "address_line":      row[11],
        "city":              row[12],
        "pincode":           row[13],
        "customer_email":    row[14],
    }


def _get_order_items(db: Session, order_id: int) -> list:
    rows = db.execute(text("""
        SELECT p."Name", oi."Quantity", oi."Price", pv."Color", s."SizeLabel"
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products" p
               ON p."ProductId" = oi."ProductId"
        LEFT JOIN twam."ProductVariantDetail" pvd
               ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
        LEFT JOIN twam."ProductVariants" pv
               ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN mdm."Size" s ON s."SizeId" = pvd."Size"
        WHERE oi."OrderId" = :order_id AND oi."DeletedInd" = false
    """), {"order_id": order_id}).fetchall()

    return [
        {
            "name":     r[0] or "Product",
            "quantity": r[1] or 1,
            "price":    float(r[2]) if r[2] else 0,
            "color":    r[3],
            "size":     r[4],
        }
        for r in rows
    ]


def _fmt(amount: float) -> str:
    return f"₹{amount:,.2f}"


# ── Email HTML helpers ────────────────────────────────────────────────────────

def _header(company_name: str) -> str:
    return f"""
    <div style="background:#f8f5f0;padding:20px;text-align:center;
                border-bottom:3px solid #8b7355;">
      <h1 style="margin:0;color:#8b7355;font-family:Georgia,serif;">{company_name}</h1>
    </div>"""


def _footer(company_name: str, support_email: str) -> str:
    return f"""
    <div style="background:#f8f5f0;padding:20px;text-align:center;
                margin-top:30px;border-top:1px solid #e5e0d8;">
      <p style="margin:0 0 10px;color:#666;font-size:14px;">
        Questions? <a href="mailto:{support_email}"
                      style="color:#8b7355;">{support_email}</a>
      </p>
      <p style="margin:0;color:#999;font-size:12px;">
        © {datetime.now().year} {company_name}. All rights reserved.
      </p>
    </div>"""


def _items_table(items: list) -> str:
    rows_html = ""
    for item in items:
        details = []
        if item.get("size"):  details.append(f"Size: {item['size']}")
        if item.get("color"): details.append(f"Color: {item['color']}")
        det = (f"<br><small style='color:#666'>{' | '.join(details)}</small>"
               if details else "")
        rows_html += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #eee;">{item['name']}{det}</td>
          <td style="padding:12px;border-bottom:1px solid #eee;
                     text-align:center;">{item['quantity']}</td>
          <td style="padding:12px;border-bottom:1px solid #eee;
                     text-align:right;">{_fmt(item['price'])}</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
      <thead>
        <tr style="background:#f8f5f0;">
          <th style="padding:12px;text-align:left;
                     border-bottom:2px solid #8b7355;">Item</th>
          <th style="padding:12px;text-align:center;
                     border-bottom:2px solid #8b7355;">Qty</th>
          <th style="padding:12px;text-align:right;
                     border-bottom:2px solid #8b7355;">Price</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


# ── HTTP SMS sender ───────────────────────────────────────────────────────────
#
# API docs (HTTP GET / POST):
#   https://domain/fe/api/v1/send
#   ?username=U&password=P&unicode=false&from=SENDER&to=10DIGIT&text=MSG&dltContentId=ID
#
# Response: {"transactionId":205538399,"state":"SUBMIT_ACCEPTED","statusCode":200}
# Error codes: 2070=auth failure, 2051=bad sender, 2054=invalid MSISDN,
#              6001=no balance, 7001=missing DLT content ID

def _send_sms(
    db: Session,
    phone: str,
    message_type: str,
    variables: dict,
) -> bool:
    """
    Send a single SMS.

    Looks up the template from mdm.MessageTemplate by message_type to get
    both the DLT Content ID (dltId) and the message body (messageContent).
    Substitutes {variable} placeholders in messageContent before sending.

    Args:
        db:           Database session.
        phone:        Customer phone number (any format — cleaned internally).
        message_type: One of the MT_* constants (e.g. MT_ORDER_PLACED).
        variables:    Dict of {variable_name: value} for template substitution.
    """
    # ── Load SMS credentials from AppSettings ────────────────────────────────
    sms_url      = _cfg(db, "SMS_API_URL")
    sms_username = _cfg(db, "SMS_API_USERNAME")
    sms_password = _cfg(db, "SMS_API_PASSWORD")
    sender_id    = _cfg(db, "SMS_SENDER_ID", "ONLYTW")
    unicode_flag = _cfg(db, "SMS_UNICODE", "false")

    if not sms_url or not sms_username or not phone:
        print(f"[SMS] Not configured (no URL or username) — skipping {message_type}")
        return False

    # ── Load template from mdm.MessageTemplate ────────────────────────────────
    template = _get_template(db, message_type)
    if not template:
        print(f"[SMS] No active template found for messageType='{message_type}' "
              f"— add a row to mdm.MessageTemplate with that messageType and "
              f"State='Active'")
        return False

    dlt_content_id = template["dltId"]
    if not dlt_content_id:
        print(f"[SMS] Template '{message_type}' exists but DLTId is empty — "
              f"fill mdm.MessageTemplate.DLTId from your DLT portal")
        return False

    message_content = template["messageContent"]
    if not message_content:
        print(f"[SMS] Template '{message_type}' has no MessageContent — fill it")
        return False

    # Render variable placeholders
    sms_text = _render_template(message_content, variables)

    # ── Clean phone number ────────────────────────────────────────────────────
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        print(f"[SMS] Invalid phone number: {phone}")
        return False
    recipient = digits[-10:]  # 10-digit without country code

    # ── Send ──────────────────────────────────────────────────────────────────
    try:
        import httpx
        params = {
            "username":     sms_username,
            "password":     sms_password,
            "unicode":      unicode_flag,
            "from":         sender_id,
            "to":           recipient,
            "text":         sms_text,
            "dltContentId": dlt_content_id,
        }
        response = httpx.get(sms_url, params=params, timeout=8)
        data = response.json()

        if data.get("statusCode") == 200 or data.get("state") == "SUBMIT_ACCEPTED":
            print(f"[SMS] Sent {message_type} to {recipient}, "
                  f"txId={data.get('transactionId')}")
            return True
        else:
            print(f"[SMS] Failed {message_type} — "
                  f"statusCode={data.get('statusCode')}, "
                  f"description={data.get('description')}")
            return False

    except Exception as e:
        print(f"[SMS] Error sending {message_type} to {phone}: {e}")
        return False


def _send_sms_bulk(
    db: Session,
    phones: list[str],
    message_type: str,
    variables: dict,
) -> bool:
    """
    Send the same SMS to multiple recipients (up to 100) via multiSend endpoint.
    """
    sms_multi_url = _cfg(db, "SMS_API_MULTI_URL") or _cfg(db, "SMS_API_URL")
    sms_username  = _cfg(db, "SMS_API_USERNAME")
    sms_password  = _cfg(db, "SMS_API_PASSWORD")
    sender_id     = _cfg(db, "SMS_SENDER_ID", "ONLYTW")
    unicode_flag  = _cfg(db, "SMS_UNICODE", "false")

    if not sms_multi_url or not sms_username or not phones:
        return False

    template = _get_template(db, message_type)
    if not template or not template["dltId"] or not template["messageContent"]:
        print(f"[SMS Bulk] Template '{message_type}' missing or incomplete")
        return False

    sms_text = _render_template(template["messageContent"], variables)
    dlt_content_id = template["dltId"]

    cleaned = []
    for phone in phones:
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 10:
            cleaned.append(digits[-10:])

    if not cleaned:
        return False

    try:
        import httpx
        params = {
            "username":     sms_username,
            "password":     sms_password,
            "unicode":      unicode_flag,
            "from":         sender_id,
            "to":           ",".join(cleaned),
            "text":         sms_text,
            "dltContentId": dlt_content_id,
        }
        response = httpx.post(sms_multi_url, params=params, timeout=10)
        data = response.json()
        ok = data.get("statusCode") == 200 or data.get("state") == "SUBMIT_ACCEPTED"
        print(f"[SMS Bulk] {message_type} → {len(cleaned)} recipients, "
              f"state={data.get('state')}")
        return ok
    except Exception as e:
        print(f"[SMS Bulk] Error {message_type}: {e}")
        return False


# ── WhatsApp ──────────────────────────────────────────────────────────────────

async def _send_whatsapp(db: Session, phone: str, message: str) -> bool:
    wa_url = _cfg(db, "WHATSAPP_API_URL")
    wa_key = _cfg(db, "WHATSAPP_API_KEY")
    if not wa_url or not phone:
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(
                wa_url,
                headers={"Authorization": f"Bearer {wa_key}"},
                json={"phone": phone, "message": message},
            )
        return True
    except Exception as e:
        print(f"[WhatsApp] Failed: {e}")
        return False


# ── Order Placed ──────────────────────────────────────────────────────────────

def send_order_placed_notification(db: Session, order_id: int) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")
    items   = _get_order_items(db, order_id)

    # Email
    if order["customer_email"]:
        subtotal    = sum(i["price"] * i["quantity"] for i in items)
        ship_charge = _fmt(order["delivery_charge"]) if order["delivery_charge"] else "FREE"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;">
            <h2 style="color:#333;margin-bottom:5px;">Thank you for your order!</h2>
            <p style="color:#666;margin-top:0;">
              Hi {order['customer_name']}, your order has been confirmed.
            </p>
            <div style="background:#f8f5f0;padding:15px;border-radius:8px;margin:20px 0;">
              <p style="margin:0;"><strong>Order Number:</strong> #{order['order_number']}</p>
              <p style="margin:5px 0 0;"><strong>Order Date:</strong>
                {datetime.now().strftime('%d %B %Y')}</p>
            </div>
            <h3 style="color:#8b7355;border-bottom:1px solid #eee;padding-bottom:10px;">
              Order Summary
            </h3>
            {_items_table(items)}
            <div style="text-align:right;padding:15px 0;border-top:2px solid #8b7355;">
              <p style="margin:5px 0;">
                <span style="color:#666;">Subtotal:</span>
                <strong>{_fmt(subtotal)}</strong>
              </p>
              <p style="margin:5px 0;">
                <span style="color:#666;">Shipping:</span>
                <strong>{ship_charge}</strong>
              </p>
              <p style="margin:10px 0 0;font-size:18px;">
                <span style="color:#666;">Total:</span>
                <strong style="color:#8b7355;">{_fmt(order['total_amount'])}</strong>
              </p>
            </div>
            <div style="background:#fff8e7;padding:15px;border-radius:8px;
                        border-left:4px solid #f5a623;margin:20px 0;">
              <p style="margin:0;color:#333;">
                📦 We'll send tracking details once your order ships!
              </p>
            </div>
            <h3 style="color:#8b7355;">Delivery Address</h3>
            <p style="color:#666;line-height:1.6;">
              {order['customer_name']}<br>
              {order['address_line'] or ''}<br>
              {order['city'] or ''} - {order['pincode'] or ''}<br>
              📞 {order['customer_phone'] or ''}
            </p>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Order Confirmed! #{order['order_number']} - {company}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_ORDER_PLACED, {
            "order_number":  order["order_number"],
            "total_amount":  _fmt(order["total_amount"]),
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    return True


# ── Order Shipped ─────────────────────────────────────────────────────────────

async def send_order_shipped_notification(db: Session, order_id: int) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company       = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support       = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")
    tracking_base = _cfg(db, "TRACKING_BASE_URL",
                         "https://app.elite.ekartlogistics.in/track")
    tracking_url  = (f"{tracking_base}/{order['tracking_id']}"
                     if order["tracking_id"] else "")

    # Email
    if order["customer_email"]:
        track_btn = (
            f'<a href="{tracking_url}" style="display:inline-block;margin-top:15px;'
            f'background:#8b7355;color:#fff;padding:12px 30px;text-decoration:none;'
            f'border-radius:5px;">Track Your Package →</a>'
            if tracking_url else ""
        )
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;">
            <div style="text-align:center;margin-bottom:30px;">
              <div style="font-size:60px;">🚚</div>
              <h2 style="color:#333;margin:10px 0;">Your order is on its way!</h2>
            </div>
            <p style="color:#666;">Hi {order['customer_name']},</p>
            <p style="color:#666;">
              Your order <strong>#{order['order_number']}</strong> has been shipped!
            </p>
            <div style="background:#f8f5f0;padding:20px;border-radius:8px;
                        margin:25px 0;text-align:center;">
              <p style="margin:0 0 10px;color:#666;">Tracking ID</p>
              <p style="margin:0;font-size:24px;font-weight:bold;color:#8b7355;
                        letter-spacing:2px;">
                {order['tracking_id'] or 'Processing...'}
              </p>
              {track_btn}
            </div>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Your Order is On Its Way! #{order['order_number']}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_ORDER_SHIPPED, {
            "order_number":  order["order_number"],
            "tracking_id":   order["tracking_id"] or "",
            "tracking_url":  tracking_url,
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    # WhatsApp
    if order["whatsapp_opted_in"] and order["customer_phone"]:
        await _send_whatsapp(db, order["customer_phone"],
            f"🚚 *Order Shipped!*\n\nHi {order['customer_name']}, "
            f"your order *#{order['order_number']}* has been shipped!\n\n"
            f"📦 *Tracking ID:* {order['tracking_id'] or 'Coming soon'}\n"
            + (f"🔗 Track: {tracking_url}" if tracking_url else "")
            + f"\n\n— {company}")

    return True


# ── Out for Delivery ──────────────────────────────────────────────────────────

async def send_out_for_delivery_notification(db: Session, order_id: int) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")

    # Email
    if order["customer_email"]:
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;text-align:center;">
            <div style="font-size:60px;">📍</div>
            <h2 style="color:#333;margin:10px 0;">Your order is arriving today!</h2>
            <p style="color:#666;font-size:16px;">
              Hi {order['customer_name']}, order
              <strong>#{order['order_number']}</strong> is out for delivery!
            </p>
            <div style="background:#e8f5e9;padding:20px;border-radius:8px;margin:25px 0;">
              <p style="margin:0;color:#2e7d32;font-size:16px;">
                📦 Please ensure someone is available to receive the package.
              </p>
            </div>
            <p style="color:#666;">
              <strong>Tracking ID:</strong> {order['tracking_id'] or 'N/A'}
            </p>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Arriving Today! Order #{order['order_number']}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_OUT_FOR_DELIVERY, {
            "order_number":  order["order_number"],
            "tracking_id":   order["tracking_id"] or "",
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    # WhatsApp
    if order["whatsapp_opted_in"] and order["customer_phone"]:
        await _send_whatsapp(db, order["customer_phone"],
            f"📍 *Out for Delivery!*\n\nHi {order['customer_name']}, "
            f"order *#{order['order_number']}* is arriving today!\n\n"
            f"Please ensure someone is home.\n\n— {company}")

    return True


# ── Delivered ─────────────────────────────────────────────────────────────────

async def send_delivery_confirmation(
    db: Session, order_id: int, pod_image_url: Optional[str] = None
) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")
    website = _cfg(db, "WEBSITE_URL", "https://onlytwam.com")

    # Email
    if order["customer_email"]:
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;text-align:center;">
            <div style="font-size:60px;">✅</div>
            <h2 style="color:#2e7d32;margin:10px 0;">
              Your order has been delivered!
            </h2>
            <p style="color:#666;font-size:16px;">
              Hi {order['customer_name']}, order
              <strong>#{order['order_number']}</strong>
              has been successfully delivered.
            </p>
            <div style="background:#f8f5f0;padding:20px;border-radius:8px;margin:25px 0;">
              <p style="margin:0 0 15px;color:#333;">We hope you love your purchase! 💝</p>
              <a href="{website}/account/orders-list"
                style="display:inline-block;background:#8b7355;color:#fff;
                       padding:12px 30px;text-decoration:none;border-radius:5px;">
                Leave a Review
              </a>
            </div>
            <p style="color:#999;font-size:14px;">
              Need to return? Visit "My Orders" to initiate a return within 7 days.
            </p>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Delivered! Order #{order['order_number']} - {company}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_ORDER_DELIVERED, {
            "order_number":  order["order_number"],
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    # WhatsApp
    if order["whatsapp_opted_in"] and order["customer_phone"]:
        await _send_whatsapp(db, order["customer_phone"],
            f"✅ *Delivered!*\n\nHi {order['customer_name']}, "
            f"order *#{order['order_number']}* has been delivered! 💝\n\n"
            f"Questions? Email {support}\n\n— {company}")

    return True


# ── Order Cancelled ───────────────────────────────────────────────────────────

def send_order_cancelled_notification(
    db: Session, order_id: int, reason: Optional[str] = None
) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")

    # Email
    if order["customer_email"]:
        reason_line = (
            f'<p style="color:#666;"><strong>Reason:</strong> {reason}</p>'
            if reason else ""
        )
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;">
            <h2 style="color:#333;">Order Cancelled</h2>
            <p style="color:#666;">Hi {order['customer_name']},</p>
            <p style="color:#666;">
              Your order <strong>#{order['order_number']}</strong> has been cancelled
              {f'— {reason}' if reason else ''}.
            </p>
            {reason_line}
            <div style="background:#f8f5f0;padding:15px;border-radius:8px;margin:20px 0;">
              <p style="margin:0;"><strong>Order Number:</strong> #{order['order_number']}</p>
              <p style="margin:5px 0 0;">
                <strong>Amount:</strong> {_fmt(order['total_amount'])}
              </p>
            </div>
            <p style="color:#666;">
              If you paid online, your refund will be processed within 5-7 business days.
            </p>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Order Cancelled - #{order['order_number']}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_ORDER_CANCELLED, {
            "order_number":  order["order_number"],
            "total_amount":  _fmt(order["total_amount"]),
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    return True


# ── Return Initiated ──────────────────────────────────────────────────────────

def send_return_initiated_notification(
    db: Session, order_id: int, return_reason: Optional[str] = None
) -> bool:
    order = _get_order_details(db, order_id)
    if not order:
        return False

    company = _cfg(db, "COMPANY_NAME", "Only TWAM")
    support = _cfg(db, "SUPPORT_EMAIL", "support@onlytwam.com")

    # Email
    if order["customer_email"]:
        reason_line = (
            f'<p style="color:#666;"><strong>Reason:</strong> {return_reason}</p>'
            if return_reason else ""
        )
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
          {_header(company)}
          <div style="padding:30px;">
            <h2 style="color:#333;">Return Request Received</h2>
            <p style="color:#666;">Hi {order['customer_name']},</p>
            <p style="color:#666;">
              We've received your return request for order
              <strong>#{order['order_number']}</strong>.
            </p>
            {reason_line}
            <div style="background:#fff8e7;padding:15px;border-radius:8px;
                        border-left:4px solid #f5a623;margin:20px 0;">
              <h4 style="margin:0 0 10px;color:#333;">What happens next?</h4>
              <ol style="margin:0;padding-left:20px;color:#666;">
                <li>Our team will review your request</li>
                <li>You'll receive pickup details within 24-48 hours</li>
                <li>Refund will be processed after we receive the item</li>
              </ol>
            </div>
            <p style="color:#666;">
              Questions? <a href="mailto:{support}" style="color:#8b7355;">{support}</a>
            </p>
          </div>
          {_footer(company, support)}
        </div>"""

        send_email(db, EmailCreate(
            name=order["customer_name"],
            email=order["customer_email"],
            subject=f"Return Request Received - #{order['order_number']}",
            message=body,
        ))

    # SMS
    if order["customer_phone"]:
        _send_sms(db, order["customer_phone"], MT_RETURN_INITIATED, {
            "order_number":  order["order_number"],
            "company_name":  company,
            "customer_name": order["customer_name"],
        })

    return True


# ── Generic status dispatcher ─────────────────────────────────────────────────

def send_order_status_notification(db: Session, order_id: int, new_status: str) -> bool:
    """
    Sync dispatcher — routes to the correct notification function.
    Safe to call from both sync (orders/repository.py) and async contexts.
    """
    import asyncio

    def _run(coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=15)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    try:
        if new_status in ("Confirmed", "Pending"):
            return send_order_placed_notification(db, order_id)
        elif new_status in ("Shipped", "Processing"):
            return _run(send_order_shipped_notification(db, order_id))
        elif new_status == "Out for Delivery":
            return _run(send_out_for_delivery_notification(db, order_id))
        elif new_status == "Delivered":
            return _run(send_delivery_confirmation(db, order_id))
        elif new_status == "Cancelled":
            return send_order_cancelled_notification(db, order_id)
        elif new_status == "Return Initiated":
            return send_return_initiated_notification(db, order_id)
    except Exception as e:
        print(f"[Notifications] send_order_status_notification failed "
              f"for order {order_id}: {e}")

    return True