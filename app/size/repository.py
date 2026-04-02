from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from typing import Optional, List
from datetime import datetime
from .models import Size


def get_all_sizes(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    query = db.query(Size).filter(
        Size.deletedInd == False,
        Size.isActive == True
    )

    query = apply_filters(query, Size, filters)

    query = apply_ordering(query, Size, order_property, order_ascending)

    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    return query.all()


def get_size_by_id(db: Session, size_id: int):
    return db.query(Size).filter(
        Size.sizeId == size_id,
        Size.deletedInd == False
    ).first()


def create_size(db: Session, size_data: dict):
    size = Size(
        **size_data,
        createdDate=datetime.now(),
        deletedInd=False
    )
    db.add(size)
    db.commit()
    db.refresh(size)
    return size


def update_size(db: Session, size_id: int, size_data: dict):
    size = get_size_by_id(db, size_id)
    if not size:
        return None
    for key, value in size_data.items():
        setattr(size, key, value)
    size.modifiedDate = datetime.now()
    db.commit()
    db.refresh(size)
    return size


def delete_size(db: Session, size_id: int):
    size = get_size_by_id(db, size_id)
    if not size:
        return None
    size.deletedInd = True
    size.modifiedDate = datetime.now()
    db.commit()
    return True