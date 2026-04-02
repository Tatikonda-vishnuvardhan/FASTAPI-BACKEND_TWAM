from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import UserReview

def _to_dict(r):
    return {
        "userReviewId":     r.userReviewId,
        "productVariantId": r.productVariantId,
        "rating":           r.rating,
        "comment":          r.comment,
        "userProfileId":    r.userProfileId,
        "state":            r.state,
        "displayName":      r.displayName,
        "email":            r.email,
        "reviewTitle":      r.reviewTitle,
        "createdDate":      r.createdDate,
    }

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(UserReview).filter(UserReview.deletedInd == False)
    if filters:
        for f in filters:
            prop = f.get("property", "")
            val  = f.get("value")
            col  = getattr(UserReview, prop, None)
            # Also try lowercase first char (camelCase mapping)
            if col is None:
                col = getattr(UserReview, prop[0].lower() + prop[1:] if prop else "", None)
            if col is not None:
                query = query.filter(col == val)
    if order_property:
        col = getattr(UserReview, order_property, None)
        if col:
            query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    else:
        query = query.order_by(desc(UserReview.createdDate))
    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def get_by_id(db: Session, review_id: int):
    r = db.query(UserReview).filter(
        UserReview.userReviewId == review_id,
        UserReview.deletedInd == False
    ).first()
    return _to_dict(r) if r else None

def create(db: Session, data) -> int:
    entity = UserReview(
        productVariantId = data.productVariantId,
        rating           = data.rating,
        comment          = data.comment,
        userProfileId    = data.userProfileId,
        state            = data.state or "Active",
        displayName      = data.displayName,
        email            = data.email,
        reviewTitle      = data.reviewTitle,
        createdDate      = datetime.now(timezone.utc),
        deletedInd       = False,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity.userReviewId

def update(db: Session, data) -> Optional[int]:
    entity = db.query(UserReview).filter(UserReview.userReviewId == data.userReviewId).first()
    if not entity: return None
    entity.rating      = data.rating
    entity.comment     = data.comment
    entity.state       = data.state
    entity.displayName = data.displayName
    entity.email       = data.email
    entity.reviewTitle = data.reviewTitle
    entity.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return entity.userReviewId