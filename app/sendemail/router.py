from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles
from app.sendemail import repository
from app.sendemail.schemas import (
    EmailCreate, EmailListResponse,
    EmailCredentialCreate, EmailCredentialUpdate, EmailCredentialListResponse
)

router = APIRouter(prefix="/api/Email", tags=["Email"])


# ─────────────────────────────────────────────────────────────────────────────
# SEND EMAIL — any logged-in user
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_200_OK,
            #  dependencies=[Depends(get_current_user)]
            )
def send_email(payload: EmailCreate, db: Session = Depends(get_db)):
    """Send an email using the active SMTP credential from the database."""
    return repository.send_email(db, payload)


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL LOG — view sent email history (Super Admin only)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=EmailListResponse,
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def get_email_logs(
    page_index: Optional[int] = Query(None, alias="page.index"),
    page_size:  Optional[int] = Query(None, alias="page.size"),
    db: Session = Depends(get_db)
):
    """View all sent/failed email log records."""
    p_index = page_index if page_index and page_index > 0 else None
    p_size  = page_size  if page_size  and page_size  > 0 else None
    return repository.get_email_list(db, p_index, p_size)


# ─────────────────────────────────────────────────────────────────────────────
# SMTP CREDENTIALS CRUD — Super Admin only
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/credentials", response_model=EmailCredentialListResponse,
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def get_credentials(db: Session = Depends(get_db)):
    """List all SMTP credential configurations."""
    return repository.get_credentials(db)


@router.post("/credentials", status_code=201,
             dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def create_credential(data: EmailCredentialCreate, db: Session = Depends(get_db)):
    """
    Add a new SMTP credential.
    If isActive=true, all other credentials are automatically deactivated.
    """
    new_id = repository.create_credential(db, data)
    return {"EmailCredentialId": new_id, "message": "Credential created successfully."}


@router.put("/credentials/{credential_id}",
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def update_credential(credential_id: int, data: EmailCredentialUpdate,
                      db: Session = Depends(get_db)):
    """Update an existing SMTP credential."""
    result = repository.update_credential(db, credential_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Credential not found.")
    return {"EmailCredentialId": result, "message": "Credential updated successfully."}


@router.delete("/credentials/{credential_id}", status_code=204,
               dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def delete_credential(credential_id: int, db: Session = Depends(get_db)):
    """Soft-delete an SMTP credential."""
    if not repository.delete_credential(db, credential_id):
        raise HTTPException(status_code=404, detail="Credential not found.")


@router.post("/credentials/{credential_id}/activate",
             dependencies=[Depends(require_roles(Roles.SUPER_ADMIN))])
def activate_credential(credential_id: int, db: Session = Depends(get_db)):
    """
    Set this credential as the active one for sending emails.
    All other credentials are automatically deactivated.
    """
    result = repository.activate_credential(db, credential_id)
    if not result:
        raise HTTPException(status_code=404, detail="Credential not found.")
    return {"EmailCredentialId": result, "message": "Credential activated successfully."}