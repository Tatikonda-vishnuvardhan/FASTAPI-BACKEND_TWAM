import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import ProductReview

BASE_URL = os.getenv("BASE_URL", "")


def _to_dict(r: ProductReview) -> dict:
    return {
        "productReviewId":  r.productReviewId,
        "productId":        r.productId,
        "productVariantId": r.productVariantId,
        "rating":           r.rating,
        "comment":          r.comment,
        "name":             r.name,
        "email":            r.email,
        "title":            r.title,
        "userProfileId":    r.userProfileId,
        "state":            r.state,
        "itemId":           r.itemId,
        # Return full URL if photo is a relative path, otherwise return as-is
        "photo":            f"{BASE_URL}{r.photo}" if r.photo and not r.photo.startswith("http") else r.photo,
        "createdDate":      r.createdDate,
        "modifiedDate":     r.modifiedDate,
    }


def get_all_reviews(db, filters, order_ascending, order_property, page_index, page_size) -> dict:
    query = db.query(ProductReview).filter(ProductReview.deletedInd == False)
    query = apply_filters(query, ProductReview, filters)
    query = apply_ordering(query, ProductReview, order_property, order_ascending)
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return build_paged_response(total, [_to_dict(r) for r in query.all()])


def get_review_by_id(db, review_id: int) -> Optional[dict]:
    r = db.query(ProductReview).filter(
        ProductReview.productReviewId == review_id,
        ProductReview.deletedInd == False
    ).first()
    return _to_dict(r) if r else None


def create_or_update_review(db, data) -> int:
    """
    Mirrors CreateProductReviewCommandHandler:
    - If itemId already has a review → update rating/comment/photo
    - Otherwise → create new
    """
    existing = db.query(ProductReview).filter(
        ProductReview.itemId == data.itemId
    ).first() if data.itemId else None

    if existing:
        existing.rating       = data.rating
        existing.comment      = data.comment
        # Only overwrite photo if a new one is provided
        if data.photo is not None:
            existing.photo    = data.photo
        existing.modifiedDate = datetime.now(timezone.utc)
        db.commit()
        return existing.productReviewId
    else:
        review = ProductReview(
            productId        = data.productId,
            productVariantId = data.productVariantId,
            rating           = data.rating,
            comment          = data.comment,
            title            = data.title,
            name             = data.name,
            email            = data.email,
            userProfileId    = data.userProfileId,
            state            = data.state or 'Active',
            itemId           = data.itemId,
            photo            = data.photo,
            createdDate      = datetime.now(timezone.utc),
            deletedInd       = False,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review.productReviewId


def update_review(db, review_id: int, data) -> Optional[int]:
    r = db.query(ProductReview).filter(
        ProductReview.productReviewId == review_id,
        ProductReview.deletedInd == False
    ).first()
    if not r:
        return None
    r.rating       = data.rating
    r.comment      = data.comment
    r.name         = data.name
    r.email        = data.email
    r.state        = data.state
    if data.photo is not None:
        r.photo    = data.photo
    r.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return r.productReviewId


def get_review_stats(db, product_variant_id: int) -> dict:
    """Mirrors GetProductReviewStatsListQueryHandler."""
    reviews = db.query(ProductReview).filter(
        ProductReview.productVariantId == product_variant_id,
        ProductReview.deletedInd == False
    ).all()

    breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews:
        if r.rating and r.rating in breakdown:
            breakdown[r.rating] += 1

    avg = round(sum(r.rating or 0 for r in reviews) / len(reviews), 2) if reviews else 0.0

    return {
        "totalReviews":  len(reviews),
        "averageRating": avg,
        "breakdown":     breakdown,
    }
