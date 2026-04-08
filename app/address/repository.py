from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import Address

def _enrich(db: Session, addr: Address) -> dict:
    state_name   = None
    country_name = None
    if addr.stateId:
        row = db.execute(
            text('SELECT "StateName" FROM mdm."State" WHERE "StateId"=:id LIMIT 1'),
            {"id": addr.stateId}
        ).fetchone()
        state_name = row[0] if row else None
    if addr.countryId:
        row = db.execute(
            text('SELECT "CountryName" FROM mdm."Country" WHERE "CountryId"=:id LIMIT 1'),
            {"id": addr.countryId}
        ).fetchone()
        country_name = row[0] if row else None
    return {
        "addressId":        addr.addressId,
        "name":             addr.name,
        "addressLine":      addr.addressLine,
        "locality":         addr.locality,
        "city":             addr.city,
        "stateId":          addr.stateId,
        "countryId":        addr.countryId,
        "pinCode":          addr.pinCode,
        "phone":            addr.phone,
        "isDefault":        addr.isDefault,
        "isBillingAddress": addr.isBillingAddress,
        "personalId":       addr.personalId,
        "typeId":           addr.typeId,
        "userProfileId":    addr.userProfileId,
        "createdDate":      addr.createdDate,
        "modifiedDate":     addr.modifiedDate,
        "stateName":        state_name,
        "countryName":      country_name,
    }


def get_all_addresses(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
) -> dict:
    query = db.query(Address).filter(Address.deletedInd == False)

    query = apply_filters(query, Address, filters)
    query = apply_ordering(query, Address, order_property, order_ascending)
    total = query.count()
    query = apply_pagination(query, page_index, page_size)
    rows  = query.all()
    return build_paged_response(total, [_enrich(db, r) for r in rows])


def get_address_by_id(db: Session, address_id: int) -> Optional[dict]:
    addr = db.query(Address).filter(
        Address.addressId == address_id,
        Address.deletedInd == False
    ).first()
    if not addr:
        return None
    return _enrich(db, addr)


def create_address(db: Session, data) -> int:
    """
    Mirrors CreateAddressCommandHandler:
    - First address for user → auto set as default
    - If new address is default → unset other defaults
    """
    addr_count = db.query(Address).filter(
        Address.userProfileId == data.userProfileId,
        Address.deletedInd == False
    ).count()
    is_default = True if addr_count == 0 else (data.isDefault or False)

    addr = Address(
        name             = data.name,
        addressLine      = data.addressLine,
        locality         = data.locality,
        city             = data.city,
        stateId          = data.stateId,
        countryId        = data.countryId,
        pinCode          = data.pinCode,
        phone            = data.phone,
        isDefault        = is_default,
        userProfileId    = data.userProfileId,
        typeId           = data.typeId,
        personalId       = data.personalId or 0,
        isBillingAddress = data.isBillingAddress,
        createdDate      = datetime.now(timezone.utc),
        deletedInd       = False,
    )
    db.add(addr)
    db.commit()
    db.refresh(addr)

    # If this is the new default and user already had addresses → clear others
    if is_default and addr_count > 0:
        db.execute(
            text("""
                UPDATE twam."Address"
                SET "IsDefault" = false
                WHERE "AddressId" != :aid
                  AND "UserProfileId" = :uid
                  AND "DeletedInd" = false
            """),
            {"aid": addr.addressId, "uid": data.userProfileId}
        )
        db.commit()

    return addr.addressId


def update_address(
    db: Session,
    address_id: int,
    data,
    current_user_id: Optional[str] = None,
    is_staff: bool = False,
) -> Optional[int]:
    """
    Mirrors UpdateAddressCommandHandler:
    - If isDefault → clear other defaults first
    """
    query = db.query(Address).filter(Address.addressId == address_id)
    if not is_staff and current_user_id:
        query = query.filter(Address.userProfileId == current_user_id)
    addr = query.first()
    if not addr:
        return None

    if data.isDefault:
        if not data.userProfileId:
            raise ValueError("userProfileId required when setting a default address.")
        db.execute(
            text("""
                UPDATE twam."Address"
                SET "IsDefault" = false
                WHERE "AddressId" != :aid
                  AND "UserProfileId" = :uid
                  AND "DeletedInd" = false
            """),
            {"aid": address_id, "uid": data.userProfileId}
        )
        db.flush()

    addr.name             = data.name
    addr.addressLine      = data.addressLine
    addr.locality         = data.locality
    addr.city             = data.city
    addr.stateId          = data.stateId
    addr.countryId        = data.countryId
    addr.pinCode          = data.pinCode
    addr.phone            = data.phone
    addr.isDefault        = data.isDefault
    addr.typeId           = data.typeId
    addr.isBillingAddress = data.isBillingAddress
    addr.modifiedDate     = datetime.now(timezone.utc)
    db.commit()
    return addr.addressId


def delete_address(
    db: Session,
    address_id: int,
    current_user_id: Optional[str] = None,
    is_staff: bool = False,
) -> bool:
    query = db.query(Address).filter(Address.addressId == address_id)
    if not is_staff and current_user_id:
        query = query.filter(Address.userProfileId == current_user_id)
    addr = query.first()
    if not addr:
        return False
    addr.deletedInd   = True
    addr.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True
