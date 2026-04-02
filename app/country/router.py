import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Country", tags=["Country"])


@router.get("/", response_model=schemas.CountryListResponse)
def get_countries(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    parsed_filters = None
    if Filters:
        try:
            parsed_filters = json.loads(Filters)
            if isinstance(parsed_filters, dict):
                parsed_filters = [parsed_filters]
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid Filters format. Expected JSON array of {property, comparison, value}.")

    countries = repository.get_all_countries(
        db=db,
        filters=parsed_filters,
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )

    response_list = [
        {
            "countryId": c.countryId,
            "countryName": c.countryName,
            "countryCode": c.countryCode,
            "isActive": c.isActive,
            "userProfileId": c.userProfileId,
            "state": c.state,
            "filters": None,
            "order": None,
            "page": None,
        }
        for c in countries
    ]

    return {
        "count": len(response_list),
        "list": response_list,
        "parameters": None,
    }


@router.get("/{country_id}", response_model=schemas.CountryResponse)
def get_country(country_id: int, db: Session = Depends(get_db)):
    country = repository.get_country_by_id(db, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    return country


@router.post("/", response_model=schemas.CountryResponse, status_code=201)
def create_country(country: schemas.CountryCreate, db: Session = Depends(get_db)):
    return repository.create_country(db, country.model_dump())


@router.put("/{country_id}", response_model=schemas.CountryResponse)
def update_country(country_id: int, country: schemas.CountryUpdate, db: Session = Depends(get_db)):
    updated = repository.update_country(db, country_id, country.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Country not found")
    return updated


@router.delete("/{country_id}", status_code=204)
def delete_country(country_id: int, db: Session = Depends(get_db)):
    result = repository.delete_country(db, country_id)
    if not result:
        raise HTTPException(status_code=404, detail="Country not found")