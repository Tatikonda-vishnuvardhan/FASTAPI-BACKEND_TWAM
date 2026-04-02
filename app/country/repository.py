from sqlalchemy.orm import Session
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from sqlalchemy import asc, desc
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response
from typing import Optional, List
from datetime import datetime
from .models import Country


def get_all_countries(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
):
    # Exclude soft-deleted records
    query = db.query(Country).filter(Country.deletedInd == False)

    # Apply Filters
    query = apply_filters(query, Country, filters)
    # Apply Ordering
    query = apply_ordering(query, Country, order_property, order_ascending)
    # Apply Pagination
    if page_index and page_size:
        offset = (page_index - 1) * page_size
        query = query.offset(offset).limit(page_size)

    return query.all()


def get_country_by_id(db: Session, country_id: int):
    return db.query(Country).filter(
        Country.countryId == country_id,
        Country.deletedInd == False
    ).first()


def create_country(db: Session, country_data: dict):
    country = Country(
        **country_data,
        createdDate=datetime.now(),
        deletedInd=False
    )
    db.add(country)
    db.commit()
    db.refresh(country)
    return country


def update_country(db: Session, country_id: int, country_data: dict):
    country = get_country_by_id(db, country_id)
    if not country:
        return None
    for key, value in country_data.items():
        setattr(country, key, value)
    country.modifiedDate = datetime.now()
    db.commit()
    db.refresh(country)
    return country


def delete_country(db: Session, country_id: int):
    # Soft delete — sets DeletedInd = True
    country = get_country_by_id(db, country_id)
    if not country:
        return None
    country.deletedInd = True
    country.modifiedDate = datetime.now()
    db.commit()
    return True