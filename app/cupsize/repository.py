from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from typing import Optional, List
from datetime import datetime
from .models import CupSize


def get_all_cupsizes(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    query = db.query(CupSize).filter(
        CupSize.deletedInd == False,
        CupSize.isActive == True
    )

    query = apply_filters(query, CupSize, filters)

    query = apply_ordering(query, CupSize, order_property, order_ascending)

    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    return query.all()


def get_cupsize_by_id(db: Session, cupsize_id: int):
    return db.query(CupSize).filter(
        CupSize.cupSizeId == cupsize_id,
        CupSize.deletedInd == False
    ).first()


def create_cupsize(db: Session, cupsize_data: dict):
    cupsize = CupSize(
        **cupsize_data,
        createdDate=datetime.now(),
        deletedInd=False
    )
    db.add(cupsize)
    db.commit()
    db.refresh(cupsize)
    return cupsize


def update_cupsize(db: Session, cupsize_id: int, cupsize_data: dict):
    cupsize = get_cupsize_by_id(db, cupsize_id)
    if not cupsize:
        return None
    for key, value in cupsize_data.items():
        setattr(cupsize, key, value)
    cupsize.modifiedDate = datetime.now()
    db.commit()
    db.refresh(cupsize)
    return cupsize


def delete_cupsize(db: Session, cupsize_id: int):
    cupsize = get_cupsize_by_id(db, cupsize_id)
    if not cupsize:
        return None
    cupsize.deletedInd = True
    cupsize.modifiedDate = datetime.now()
    db.commit()
    return True