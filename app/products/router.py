# app/products/router.py
# FIX: Removed router-level auth that blocked guests from browsing products.
#      Auth is now per-route on write operations only (POST, PUT, DELETE).

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

# No global dependencies= here — public browse must work unauthenticated
router = APIRouter(prefix="/api/Products", tags=["Products"])


def parse_filters(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Filters format.")


# ── PUBLIC: list products (guests + logged-in users) ─────────────────────────
@router.get("/", response_model=schemas.ProductListResponse)
def get_products(
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index", ge=1),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size",  ge=1),
    db: Session = Depends(get_db),
):
    return repository.get_all_products(
        db=db,
        filters=parse_filters(Filters),
        order_ascending=Order_Ascending,
        order_property=Order_Property,
        page_index=Page_Index,
        page_size=Page_Size,
    )


# ── PUBLIC: get single product ────────────────────────────────────────────────
@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    result = repository.get_product_by_id(db, product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found.")
    return result


# ── PROTECTED: create product (staff only) ────────────────────────────────────
@router.post("/", status_code=201,
             dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def create_product(command: schemas.ProductCreate, db: Session = Depends(get_db)):
    new_id = repository.create_product(db, command)
    return {"productId": new_id}


# ── PROTECTED: update product ─────────────────────────────────────────────────
@router.put("/{product_id}",
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER,
                                                Roles.INVENTORY_MANAGER))])
def update_product(product_id: int, command: schemas.ProductUpdate, db: Session = Depends(get_db)):
    result = repository.update_product(db, product_id, command)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"productId": result}


# ── PROTECTED: delete product ─────────────────────────────────────────────────
@router.delete("/{product_id}", status_code=204,
               dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    result = repository.delete_product(db, product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found.")


# ── PROTECTED: validate product ───────────────────────────────────────────────
@router.post("/CheckProductValidations", response_model=schemas.ProductValidationResponse,
             dependencies=[Depends(get_current_user)])
def check_product_validations(command: schemas.ProductValidationRequest, db: Session = Depends(get_db)):
    is_valid = repository.check_product_validations(db, command.productId, command.state)
    return {"isValid": is_valid}