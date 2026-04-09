import os
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(prefix="/api/ProductReview", tags=["ProductReview"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
BASE_URL   = os.getenv("BASE_URL", "")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def parse_filters(raw):
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


def _save_photo(file: UploadFile) -> str:
    """Save the uploaded photo to disk and return its relative path."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{file.content_type}'. Allowed: jpeg, png, webp, gif."
        )
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    disk_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(disk_path, "wb") as f:
        f.write(file.file.read())
    return f"/{UPLOAD_DIR}/{unique_name}"


# ---------------------------------------------------------------------------
# GET endpoints (unchanged)
# ---------------------------------------------------------------------------

@router.get("", response_model=schemas.ProductReviewListResponse)
def get_reviews(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size",  ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_all_reviews(
        db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size
    )


@router.get("/{review_id}", response_model=schemas.ProductReviewResponse)
def get_review(review_id: int, db: Session = Depends(get_db)):
    result = repository.get_review_by_id(db, review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found.")
    return result


# ---------------------------------------------------------------------------
# POST  — multipart/form-data so the photo file can be attached optionally.
# All review fields are sent as Form fields; photo is an optional UploadFile.
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def create_review(
    productId:        Optional[int]  = Form(None),
    productVariantId: Optional[int]  = Form(None),
    rating:           Optional[int]  = Form(None),
    comment:          Optional[str]  = Form(None),
    userProfileId:    Optional[str]  = Form(None),
    state:            Optional[str]  = Form(None),
    name:             Optional[str]  = Form(None),
    email:            Optional[str]  = Form(None),
    title:            Optional[str]  = Form(None),
    itemId:           Optional[int]  = Form(None),
    photo:            Optional[UploadFile] = File(None),   # ← optional photo
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    photo_path: Optional[str] = None
    if photo and photo.filename:          # file was actually attached
        photo_path = _save_photo(photo)

    command = schemas.ProductReviewCreate(
        productId=productId,
        productVariantId=productVariantId,
        rating=rating,
        comment=comment,
        userProfileId=userProfileId,
        state=state,
        name=name,
        email=email,
        title=title,
        itemId=itemId,
        photo=photo_path,
    )
    result = repository.create_or_update_review(db, command)
    return {"productReviewId": result}


# ---------------------------------------------------------------------------
# PUT  — same multipart approach so the photo can be updated too.
# ---------------------------------------------------------------------------

@router.put("/{review_id}")
def update_review(
    review_id:        int,
    productId:        Optional[int]  = Form(None),
    productVariantId: Optional[int]  = Form(None),
    rating:           Optional[int]  = Form(None),
    comment:          Optional[str]  = Form(None),
    userProfileId:    Optional[str]  = Form(None),
    state:            Optional[str]  = Form(None),
    name:             Optional[str]  = Form(None),
    email:            Optional[str]  = Form(None),
    title:            Optional[str]  = Form(None),
    itemId:           Optional[int]  = Form(None),
    photo:            Optional[UploadFile] = File(None),   # ← optional photo
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    photo_path: Optional[str] = None
    if photo and photo.filename:
        photo_path = _save_photo(photo)

    command = schemas.ProductReviewUpdate(
        productReviewId=review_id,
        productId=productId,
        productVariantId=productVariantId,
        rating=rating,
        comment=comment,
        userProfileId=userProfileId,
        state=state,
        name=name,
        email=email,
        title=title,
        itemId=itemId,
        photo=photo_path,
    )
    result = repository.update_review(db, review_id, command)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"productReviewId": result}


# ---------------------------------------------------------------------------
# Stats (unchanged)
# ---------------------------------------------------------------------------

@router.post("/GetProductReviewStats", response_model=schemas.ProductReviewStatsResponse)
def get_review_stats(query: schemas.ProductReviewStatsRequest, db: Session = Depends(get_db)):
    return repository.get_review_stats(db, query.productVariantId)