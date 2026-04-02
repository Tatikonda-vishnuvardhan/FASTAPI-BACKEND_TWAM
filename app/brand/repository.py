from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from typing import Optional, List
from .models import Brand


def get_all_brands(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    query = db.query(Brand)

    # Apply Filters
    query = apply_filters(query, Brand, filters)
    # Apply Ordering
    query = apply_ordering(query, Brand, order_property, order_ascending)

    # Apply Pagination
    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    return query.all()


def get_brand_by_id(db: Session, brand_id: int):
    return db.query(Brand).filter(Brand.brandId == brand_id).first()


def create_brand(db: Session, brand_data: dict):
    brand = Brand(**brand_data)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def update_brand(db: Session, brand_id: int, brand_data: dict):
    brand = get_brand_by_id(db, brand_id)
    if not brand:
        return None
    for key, value in brand_data.items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return brand


def delete_brand(db: Session, brand_id: int):
    brand = get_brand_by_id(db, brand_id)
    if not brand:
        return None
    db.delete(brand)
    db.commit()
    return True