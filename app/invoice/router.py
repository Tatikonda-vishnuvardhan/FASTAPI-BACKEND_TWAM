from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Invoice", tags=["Invoice"])


@router.get("/{order_id}", response_model=schemas.InvoiceResponse)
def get_invoice(order_id: int, db: Session = Depends(get_db)):
    result = repository.get_invoice_by_order_id(db, order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found for this order.")
    return result