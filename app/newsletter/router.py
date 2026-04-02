from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from app.newsletter import repository
from app.newsletter.repository import API_BASE, FRONTEND_BASE
from app.newsletter.schemas import NewsletterSubscribe, NewsletterUnsubscribe, NewsletterBlast
from app.auth.dependencies import require_roles, Roles

router = APIRouter(prefix="/api/Newsletter", tags=["Newsletter"])


# ── Subscribe ─────────────────────────────────────────────────────────────────

@router.post("/Subscribe")
def subscribe(payload: NewsletterSubscribe, db: Session = Depends(get_db)):
    """
    Subscribe an email.
    - Checks duplicate (returns already_subscribed if exists and active)
    - Saves to Newsletter table with full audit columns
    - Sends welcome email via existing SMTP credential (with unsubscribe link)
    Returns: { "status": "new" | "already_subscribed" | "resubscribed" }
    """
    status = repository.subscribe(db, payload.email)
    return {"status": status}


# ── Unsubscribe via GET — called directly from email button link ──────────────

@router.get("/Unsubscribe", response_class=HTMLResponse)
def unsubscribe_via_link(token: str, db: Session = Depends(get_db)):
    """
    GET — called from email unsubscribe button.
    Updates DB and returns a self-contained HTML confirmation page directly.
    No redirect needed — works cross-origin from any email client.
    """
    import base64
    try:
        email = base64.b64decode(token).decode()
        assert "@" in email
    except Exception:
        return _page("❌", "#A84C6B", "Invalid Link",
                     "This unsubscribe link is invalid or has expired.",
                     show_email=False)

    result = repository.unsubscribe(db, email)
    print(f"✅ Unsubscribe GET: email={email}, found={result}")
    return _page("✓", "#6B0F2A",
                 "You have been unsubscribed",
                 f"<strong>{email}</strong> has been successfully removed from our marketing emails.<br><br>"
                 "You will still receive order confirmations and important account updates.",
                 show_email=False)


# ── Unsubscribe via POST — called from frontend if needed ─────────────────────

@router.post("/Unsubscribe")
def unsubscribe_api(
    token: str = None,
    payload: NewsletterUnsubscribe = None,
    db: Session = Depends(get_db)
):
    """
    Two uses:
    1. RFC 8058 one-click: Gmail/Outlook POST to ?token=xxx with body 'List-Unsubscribe=One-Click'
       Email client handles it silently — user never leaves their inbox.
    2. Frontend POST with JSON body { email } — footer unsubscribe button.
    """
    import base64

    # One-click from email client (token in query param)
    if token:
        try:
            email = base64.b64decode(token).decode()
            repository.unsubscribe(db, email)
            return {"status": "unsubscribed"}
        except Exception:
            return {"status": "invalid_token"}

    # Frontend call (email in JSON body)
    if payload and payload.email:
        found = repository.unsubscribe(db, payload.email)
        return {"status": "unsubscribed" if found else "not_found"}

    return {"status": "error"}


# ── Check ─────────────────────────────────────────────────────────────────────

@router.get("/Check")
def check(email: str, db: Session = Depends(get_db)):
    """Check if email is actively subscribed."""
    return {"email": email, "isSubscribed": repository.check_subscribed(db, email)}


# ── List subscribers (admin) ──────────────────────────────────────────────────

@router.get("/Subscribers", dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def list_subscribers(db: Session = Depends(get_db)):
    """Admin: list all active subscriber emails and count."""
    emails = repository.list_active_subscribers(db)
    return {"count": len(emails), "list": emails}


# ── Send blast to all subscribers (admin) ─────────────────────────────────────

@router.post("/Blast", dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def send_blast(payload: NewsletterBlast, db: Session = Depends(get_db)):
    """
    Admin: Send a marketing email to ALL active subscribers.
    - Uses existing SMTP credential from EmailCredential table
    - Each email gets a personal unsubscribe link (GET /api/Newsletter/Unsubscribe?token=...)
    - Returns { total, sent, failed, failed_emails }

    Connect to admin panel 'Send Update' button:
      POST /api/Newsletter/Blast
      { "subject": "...", "body_html": "<p>...</p>", "sent_by": "admin@twam.com" }
    """
    result = repository.send_blast(
        db,
        subject   = payload.subject,
        body_html = payload.body_html,
        sent_by   = payload.sent_by,
    )
    return result

def _page(icon: str, color: str, title: str, body: str, show_email: bool = True) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — TWAM</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{min-height:100vh;display:flex;align-items:center;justify-content:center;
         background:#F5F0E6;font-family:'Trebuchet MS',Arial,sans-serif;padding:20px}}
    .card{{background:#fff;border-radius:16px;padding:48px 40px;max-width:460px;
           width:100%;text-align:center;box-shadow:0 8px 32px rgba(107,15,42,.12);
           border:1px solid #e8d0d8}}
    .icon{{width:80px;height:80px;border-radius:50%;background:rgba(107,15,42,.08);
           display:flex;align-items:center;justify-content:center;margin:0 auto 24px;font-size:40px}}
    h1{{color:{color};font-size:24px;font-weight:700;margin-bottom:12px}}
    p{{color:#555;font-size:14px;line-height:1.7;margin-bottom:8px}}
    .btn{{display:inline-block;margin-top:28px;padding:12px 36px;background:#6B0F2A;
          color:#fff;border-radius:8px;text-decoration:none;font-size:14px;
          font-weight:700;box-shadow:0 4px 14px rgba(107,15,42,.25)}}
    .btn:hover{{background:#9E6070}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon" style="color:{color}">{icon}</div>
    <h1>{title}</h1>
    <p>{body}</p>
    <a class="btn" href="{FRONTEND_BASE}">Back to TWAM</a>
  </div>
</body>
</html>"""