import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/FileUpload", tags=["FileUpload"])

@router.get("/", response_model=schemas.FileUploadListResponse)
def get_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all(db, json.loads(Filters) if Filters else None,
                              Order_Ascending, Order_Property, Page_Index, Page_Size)

@router.post("/", status_code=201)
def create(command: schemas.FileUploadCreate, db: Session = Depends(get_db)):
    return {"fileUploadId": repository.create(db, command)}