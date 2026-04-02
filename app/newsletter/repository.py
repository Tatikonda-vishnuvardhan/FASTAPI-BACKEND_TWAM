import base64
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .models import Newsletter
from app.sendemail.repository import send_email
from app.sendemail.schemas import EmailCreate


API_BASE      = "http://127.0.0.1:8000"   # Backend — change to https://api.onlytwam.com in prod
FRONTEND_BASE = "http://localhost:5173"    # Frontend — change to https://onlytwam.com in prod


def _token(email: str) -> str:
    return base64.b64encode(email.lower().strip().encode()).decode()


def _unsubscribe_url(email: str) -> str:
    return f"{API_BASE}/api/Newsletter/Unsubscribe?token={_token(email)}"


def _footer_html(email: str, is_transactional: bool = False) -> str:
    unsub_block = "" if is_transactional else f"""
      <div style="margin:16px 0 8px;">
        <a href="{_unsubscribe_url(email)}"
           style="display:inline-block;padding:10px 28px;background:#6B0F2A;color:#ffffff;
                  font-size:13px;font-weight:600;text-decoration:none;border-radius:6px;
                  font-family:Arial,sans-serif;">
          Unsubscribe
        </a>
      </div>"""
    return f"""
    <div style="margin-top:32px;padding-top:20px;border-top:1px solid #e8d0d8;
                text-align:center;font-size:12px;color:#888;font-family:Arial,sans-serif;">
      <p style="margin:0 0 4px;">You are receiving this because you subscribed to TWAM updates.</p>
      {unsub_block}
      <p style="margin:8px 0 0;font-size:11px;color:#bbb;">
        TWAM &middot; GSM Mall, Miyapur Main Rd, Hyderabad 500050
      </p>
    </div>"""


def wrap_marketing_email(recipient_email: str, body_html: str) -> str:
    unsub_url = _unsubscribe_url(recipient_email)
    return f"""
    <div style="max-width:600px;margin:0 auto;font-family:'Trebuchet MS',Arial,sans-serif;color:#1a0a10;">

      <!-- Top unsubscribe bar -->
      <div style="background:#f9f3f5;padding:8px 20px;text-align:right;border-bottom:1px solid #e8d0d8;">
        <a href="{unsub_url}"
           style="display:inline-block;padding:6px 18px;background:#6B0F2A;color:#ffffff;
                  font-size:12px;font-weight:600;text-decoration:none;border-radius:4px;
                  font-family:Arial,sans-serif;">
          Unsubscribe
        </a>
      </div>

      <!-- TWAM header -->
      <div style="background:#6B0F2A;padding:20px 32px;text-align:center;">
        <h2 style="color:#F5F0E6;margin:0;font-size:22px;letter-spacing:2px;">TWAM</h2>
      </div>

      <!-- Email body -->
      <div style="padding:32px 24px;">{body_html}</div>

      {_footer_html(recipient_email, is_transactional=True)}
    </div>"""


# ── CRUD ──────────────────────────────────────────────────────────────────────

def check_subscribed(db: Session, email: str) -> bool:
    row = db.query(Newsletter).filter(
        Newsletter.email      == email.lower().strip(),
        Newsletter.deletedInd == False,
    ).first()
    return row is not None and row.isActive is True


def subscribe(db: Session, email: str,
              created_by: Optional[str] = None,
              org_id: Optional[int] = None) -> str:
    normalized = email.lower().strip()
    row = db.query(Newsletter).filter(Newsletter.email == normalized).first()

    if row:
        if row.isActive:
            return "already_subscribed"
        row.isActive     = True
        row.modifiedDate = datetime.now(timezone.utc)
        row.modifiedBy   = created_by
        db.commit()
        status = "resubscribed"
    else:
        row = Newsletter(
            email=normalized, isActive=True,
            createdBy=created_by, organizationId=org_id,
        )
        db.add(row)
        db.commit()
        status = "new"

    welcome_body = f"""
      <h2 style="color:#6B0F2A;">Welcome to TWAM!</h2>
      <p>Thank you for subscribing. You will be the first to know about
         new arrivals, exclusive offers, and comfort tips.</p>
      <p style="margin-top:24px;">
        <a href="{FRONTEND_BASE}/user-products/product-list"
           style="background:#6B0F2A;color:#fff;padding:12px 28px;
                  border-radius:8px;text-decoration:none;font-weight:600;">
          Shop Now
        </a>
      </p>"""
    try:
        send_email(db, EmailCreate(
            email=normalized,
            subject="Welcome to TWAM — You're subscribed!",
            message=wrap_marketing_email(normalized, welcome_body),
        ))
    except Exception as e:
        print(f"❌ Welcome email failed (subscription saved): {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    return status


def unsubscribe(db: Session, email: str,
                modified_by: Optional[str] = None) -> bool:
    normalized = email.lower().strip()
    row = db.query(Newsletter).filter(Newsletter.email == normalized).first()
    if not row:
        return False
    row.isActive     = False
    row.modifiedDate = datetime.now(timezone.utc)
    row.modifiedBy   = modified_by
    db.commit()
    return True


def list_active_subscribers(db: Session) -> list:
    rows = db.query(Newsletter).filter(
        Newsletter.isActive   == True,
        Newsletter.deletedInd == False,
    ).all()
    return [r.email for r in rows]


# ── Blast email ───────────────────────────────────────────────────────────────

def send_blast(db: Session, subject: str, body_html: str,
               sent_by: Optional[str] = None) -> dict:
    subscribers = list_active_subscribers(db)
    sent = failed = 0
    failed_emails = []

    for email in subscribers:
        full_html = wrap_marketing_email(email, body_html)
        success = send_email(db, EmailCreate(
            email=email,
            subject=subject,
            message=full_html,
            name=sent_by,
        ))
        if success:
            sent += 1
        else:
            failed += 1
            failed_emails.append(email)

    print(f"Blast done: {sent} sent, {failed} failed / {len(subscribers)} total")
    return {
        "total":         len(subscribers),
        "sent":          sent,
        "failed":        failed,
        "failed_emails": failed_emails,
    }