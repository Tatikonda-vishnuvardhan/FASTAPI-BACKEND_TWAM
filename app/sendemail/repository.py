import json
import smtplib
from datetime import datetime, timezone
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from sqlalchemy.orm import Session

from .models   import Email, EmailCredential
from .schemas  import EmailCreate, EmailCredentialCreate, EmailCredentialUpdate


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_data(data) -> Optional[str]:
    if not data:
        return None
    try:
        return json.dumps({k: v.model_dump() for k, v in data.items()})
    except Exception:
        return None


def _get_active_credential(db: Session) -> Optional[EmailCredential]:
    """Fetch the active SMTP credential row from DB."""
    return db.query(EmailCredential).filter(
        EmailCredential.isActive   == True,
        EmailCredential.deletedInd == False
    ).first()


# ─────────────────────────────────────────────────────────────────────────────
# SEND EMAIL — credentials fetched from DB
# ─────────────────────────────────────────────────────────────────────────────

def send_email(db: Session, payload: EmailCreate) -> bool:
    sent = False

    # ── Fetch SMTP credentials from database ──────────────────────────────────
    cred = _get_active_credential(db)
    if not cred:
        print("❌ No active SMTP credentials found in twam.EmailCredential table.")
        print("   Add credentials via POST /api/Email/credentials")
        _save_log(db, payload, sent=False)
        return False

    print(f"📧 Sending email to {payload.email} via {cred.smtpHost}:{cred.smtpPort} as {cred.smtpUser}")

    try:
        body_raw = payload.message or ""
        is_html  = body_raw.lstrip().startswith("<")

        msg            = MIMEMultipart("alternative")
        msg["From"]    = f"{cred.displayName} <{cred.smtpUser}>" if cred.displayName else cred.smtpUser
        msg["To"]      = payload.email or ""
        msg["Subject"] = payload.subject or ""

        # Add List-Unsubscribe header — Gmail shows "Unsubscribe" button next to sender
        if payload.email:
            import base64
            token = base64.b64encode(payload.email.lower().strip().encode()).decode()
            unsub_url = f"https://onlytwam.com/api/Newsletter/Unsubscribe?token={token}"
            msg["List-Unsubscribe"] = f"<{unsub_url}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        if is_html:
            import re
            plain_fallback = re.sub(r"<[^>]+>", "", body_raw).strip()
            plain_fallback = re.sub(r"\n{3,}", "\n\n", plain_fallback)
            msg.attach(MIMEText(plain_fallback, "plain"))
            msg.attach(MIMEText(body_raw, "html"))
        else:
            msg.attach(MIMEText(f"Name: {payload.name}\n\n{body_raw}", "plain"))

        # Port 465 = SSL, Port 587/25 = STARTTLS
        if cred.smtpPort == 465:
            with smtplib.SMTP_SSL(cred.smtpHost, cred.smtpPort, timeout=30) as server:
                server.login(cred.smtpUser, cred.smtpPassword)
                server.sendmail(cred.smtpUser, payload.email, msg.as_string())
        else:
            with smtplib.SMTP(cred.smtpHost, cred.smtpPort, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cred.smtpUser, cred.smtpPassword)
                server.sendmail(cred.smtpUser, payload.email, msg.as_string())

        sent = True
        print(f"✅ Email sent successfully to {payload.email}")

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"❌ SMTP Connection failed: {e}")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

    _save_log(db, payload, sent)
    return sent


def _save_log(db: Session, payload: EmailCreate, sent: bool):
    """Save email attempt to the Email log table."""
    try:
        # Only rollback if there's an active failed transaction
        if db.is_active and db.dirty:
            db.rollback()
        db.add(Email(
            name     = payload.name,
            subject  = payload.subject,
            email    = payload.email,
            message  = payload.message,
            filename = payload.filename,
            isFile   = payload.isFile,
            data     = _serialize_data(payload.data),
            isSent   = sent,
        ))
        db.commit()
    except Exception as e:
        print(f"❌ DB log save failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL LOG — read sent email history
# ─────────────────────────────────────────────────────────────────────────────

def get_email_list(db: Session, page_index: Optional[int] = None,
                   page_size: Optional[int] = None) -> dict:
    query = db.query(Email).order_by(Email.createdDate.desc())
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    rows = query.all()
    return {
        "count": total,
        "list": [{
            "EmailId":     r.EmailId,
            "name":        r.name,
            "subject":     r.subject,
            "email":       r.email,
            "message":     r.message,
            "isSent":      r.isSent,
            "createdDate": r.createdDate,
        } for r in rows]
    }


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL CREDENTIALS CRUD
# ─────────────────────────────────────────────────────────────────────────────

def get_credentials(db: Session) -> dict:
    rows = db.query(EmailCredential).filter(
        EmailCredential.deletedInd == False
    ).order_by(EmailCredential.EmailCredentialId).all()
    return {
        "count": len(rows),
        "list": [{
            "EmailCredentialId": r.EmailCredentialId,
            "smtpHost":          r.smtpHost,
            "smtpPort":          r.smtpPort,
            "smtpUser":          r.smtpUser,
            "smtpPassword":      r.smtpPassword,
            "displayName":       r.displayName,
            "isActive":          r.isActive,
            "createdDate":       r.createdDate,
            "modifiedDate":      r.modifiedDate,
        } for r in rows]
    }


def create_credential(db: Session, data: EmailCredentialCreate) -> int:
    # If new credential is active, deactivate all others
    if data.isActive:
        db.query(EmailCredential).filter(
            EmailCredential.deletedInd == False
        ).update({"isActive": False})

    cred = EmailCredential(
        smtpHost     = data.smtpHost,
        smtpPort     = data.smtpPort or 587,
        smtpUser     = data.smtpUser,
        smtpPassword = data.smtpPassword,
        displayName  = data.displayName,
        isActive     = data.isActive if data.isActive is not None else True,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred.EmailCredentialId


def update_credential(db: Session, credential_id: int,
                      data: EmailCredentialUpdate) -> Optional[int]:
    cred = db.query(EmailCredential).filter(
        EmailCredential.EmailCredentialId == credential_id,
        EmailCredential.deletedInd        == False
    ).first()
    if not cred:
        return None

    # If activating this one, deactivate all others
    if data.isActive is True:
        db.query(EmailCredential).filter(
            EmailCredential.EmailCredentialId != credential_id,
            EmailCredential.deletedInd        == False
        ).update({"isActive": False})

    if data.smtpHost     is not None: cred.smtpHost     = data.smtpHost
    if data.smtpPort     is not None: cred.smtpPort     = data.smtpPort
    if data.smtpUser     is not None: cred.smtpUser     = data.smtpUser
    if data.smtpPassword is not None: cred.smtpPassword = data.smtpPassword
    if data.displayName  is not None: cred.displayName  = data.displayName
    if data.isActive     is not None: cred.isActive     = data.isActive

    cred.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return cred.EmailCredentialId


def delete_credential(db: Session, credential_id: int) -> bool:
    cred = db.query(EmailCredential).filter(
        EmailCredential.EmailCredentialId == credential_id,
        EmailCredential.deletedInd        == False
    ).first()
    if not cred:
        return False
    cred.deletedInd   = True
    cred.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True


def activate_credential(db: Session, credential_id: int) -> Optional[int]:
    """Set one credential as active and deactivate all others."""
    cred = db.query(EmailCredential).filter(
        EmailCredential.EmailCredentialId == credential_id,
        EmailCredential.deletedInd        == False
    ).first()
    if not cred:
        return None
    db.query(EmailCredential).filter(
        EmailCredential.deletedInd == False
    ).update({"isActive": False})
    cred.isActive     = True
    cred.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return cred.EmailCredentialId