import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, Query, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from . import models, schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    prefix="/api/Brand",
    tags=["Brand"],
)

UPLOAD_DIR = "uploads"


# ── PUBLIC: list / fetch brands (guests can browse) ───────────────────────────

@router.get("", response_model=schemas.BrandListResponse)
def get_brands(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db),
):
    parsed_filters = None
    if Filters:
        try:
            parsed_filters = json.loads(Filters)
            if isinstance(parsed_filters, dict):
                parsed_filters = [parsed_filters]
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Invalid Filters format. Expected JSON array of {property, comparison, value}.",
            )

    brands = repository.get_all_brands(
        db=db,
        filters=parsed_filters,
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )

    response_list = [
        {
            "brandId":          brand.brandId,
            "brandName":        brand.brandName,
            "brandDescription": brand.brandDescription,
            "brandImage":       brand.brandImage,
            "brandLogo":        brand.brandLogo,
            "userProfileId":    brand.userProfileId,
            "state":            brand.state,
            "isActive":         brand.isActive,
            "filters":          None,
            "order":            None,
            "page":             None,
        }
        for brand in brands
    ]

    return {"count": len(response_list), "list": response_list, "parameters": None}


@router.get("/{brand_id}", response_model=schemas.BrandResponse)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    brand = repository.get_brand_by_id(db, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


# ── PROTECTED: create / update / delete (admin only) ─────────────────────────

@router.post(
    "/",
    response_model=schemas.BrandResponse,
    status_code=201,
    dependencies=[Depends(get_current_user)],
)
def create_brand(
    brandName:        str                  = Form(...),
    brandDescription: Optional[str]        = Form(None),
    userProfileId:    Optional[str]        = Form(None),
    state:            Optional[str]        = Form(None),
    isActive:         bool                 = Form(True),
    brandLogo:        Optional[UploadFile] = File(None),
    brandImage:       Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    brand_data: dict = {
        "brandName":        brandName,
        "brandDescription": brandDescription,
        "userProfileId":    userProfileId,
        "state":            state,
        "isActive":         isActive,
        "brandLogo":        None,
        "brandImage":       None,
    }

    if brandLogo and brandLogo.filename:
        logo_path = os.path.join(UPLOAD_DIR, brandLogo.filename)
        with open(logo_path, "wb") as f:
            shutil.copyfileobj(brandLogo.file, f)
        brand_data["brandLogo"] = logo_path

    if brandImage and brandImage.filename:
        image_path = os.path.join(UPLOAD_DIR, brandImage.filename)
        with open(image_path, "wb") as f:
            shutil.copyfileobj(brandImage.file, f)
        brand_data["brandImage"] = image_path

    return repository.create_brand(db, brand_data)


@router.put(
    "/{brand_id}",
    response_model=schemas.BrandResponse,
    dependencies=[Depends(get_current_user)],
)
def update_brand(
    brand_id:         int,
    brandName:        Optional[str]        = Form(None),
    brandDescription: Optional[str]        = Form(None),
    userProfileId:    Optional[str]        = Form(None),
    state:            Optional[str]        = Form(None),
    isActive:         Optional[bool]       = Form(None),
    brandLogo:        Optional[UploadFile] = File(None),
    brandImage:       Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    existing = repository.get_brand_by_id(db, brand_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Brand not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    brand_data: dict = {}
    if brandName        is not None: brand_data["brandName"]        = brandName
    if brandDescription is not None: brand_data["brandDescription"] = brandDescription
    if userProfileId    is not None: brand_data["userProfileId"]    = userProfileId
    if state            is not None: brand_data["state"]            = state
    if isActive         is not None: brand_data["isActive"]         = isActive

    if brandLogo and brandLogo.filename:
        logo_path = os.path.join(UPLOAD_DIR, brandLogo.filename)
        with open(logo_path, "wb") as f:
            shutil.copyfileobj(brandLogo.file, f)
        brand_data["brandLogo"] = logo_path

    if brandImage and brandImage.filename:
        image_path = os.path.join(UPLOAD_DIR, brandImage.filename)
        with open(image_path, "wb") as f:
            shutil.copyfileobj(brandImage.file, f)
        brand_data["brandImage"] = image_path

    return repository.update_brand(db, brand_id, brand_data)


@router.delete(
    "/{brand_id}",
    status_code=204,
    dependencies=[Depends(get_current_user)],
)
def delete_brand(brand_id: int, db: Session = Depends(get_db)):
    result = repository.delete_brand(db, brand_id)
    if not result:
        raise HTTPException(status_code=404, detail="Brand not found")