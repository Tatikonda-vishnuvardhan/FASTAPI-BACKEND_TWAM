from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Common", tags=["Common"])


@router.get("/GetRemarksHistory", response_model=List[schemas.RemarksHistoryResponse])
def get_remarks_history(
    dataprofile: str = Query(...),
    id: int = Query(...),
    db: Session = Depends(get_db)
):
    results = repository.get_remarks_history(db, dataprofile, id)
    if results is None:
        raise HTTPException(status_code=404, detail="No remarks history found")
    return results