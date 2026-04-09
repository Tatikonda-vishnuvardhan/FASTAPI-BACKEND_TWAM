import re
import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from app.auth.dependencies import get_current_user, Roles
from . import schemas, repository
from app.productvariant import repository as variant_repo
import sqlalchemy

router = APIRouter(prefix="/api/ProductVariantDetail", tags=["ProductVariantDetail"])


def parse_filters(raw):
    if not raw: return None
    try:
        p = json.loads(raw)
        return p if isinstance(p, list) else [p]
    except: raise HTTPException(400, "Invalid Filters format.")


def parse_angular_filters(request: Request) -> List[Dict]:
    raw = dict(request.query_params)
    bucket: Dict[int, Dict] = {}
    for key, value in raw.items():
        m = re.match(r'filters\[(\d+)\]\.(\w+)$', key, re.IGNORECASE)
        if m:
            idx = int(m.group(1))
            field = m.group(2).lower()
            if idx not in bucket:
                bucket[idx] = {}
            bucket[idx][field] = value
    result = []
    for i in sorted(bucket.keys()):
        f = bucket[i]
        if f.get("property") and f.get("value") not in (None, ""):
            result.append({
                "property":   f["property"],
                "comparison": f.get("comparison", "contains"),
                "value":      f["value"],
            })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC endpoints — MUST be defined BEFORE /{pvd_id} catch-all
# FastAPI matches routes top-to-bottom, so specific paths must come first
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/UserProductVariantDetail", response_model=schemas.UserProductListResponse)
def get_user_product_list(
    request: Request,
    page_index:      Optional[int]  = Query(None, alias="page.index"),
    page_size:       Optional[int]  = Query(None, alias="page.size"),
    order_property:  Optional[str]  = Query(None, alias="order.property"),
    order_ascending: Optional[bool] = Query(None, alias="order.ascending"),
    db: Session = Depends(get_db)
):
    filters    = parse_angular_filters(request)
    p_index    = page_index  if page_index  and page_index  > 0 else 1
    p_size     = page_size   if page_size   and page_size   > 0 else 10
    order_asc  = order_ascending if order_ascending is not None else False
    order_prop = order_property or "ModifiedDate"
    return variant_repo.get_user_product_list(
        db, filters, p_index, p_size, order_prop, order_asc
    )


@router.get("/UserProductVariant/{variant_id}")
def get_user_product_variant(variant_id: int, db: Session = Depends(get_db)):
    result = variant_repo.get_user_product_variant(db, product_variant_id=variant_id)
    if not result: raise HTTPException(404, "Product variant not found.")
    return result


@router.get("/Product", response_model=schemas.UserProductListResponse)
def get_product_by_name(name: str = Query(...), db: Session = Depends(get_db)):
    result = variant_repo.get_user_product_variant(db, name=name)
    if not result: raise HTTPException(404, "Product not found.")
    return result


@router.get("/NewArrivals", response_model=schemas.UserProductListResponse)
def get_new_arrivals(
    page_index: Optional[int] = Query(1,  alias="page.index"),
    page_size:  Optional[int] = Query(40, alias="page.size"),
    db: Session = Depends(get_db)
):
    """
    Return product variants added in the last 6 months, newest first.
    Public endpoint — no authentication required.
    """
    return variant_repo.get_new_arrivals(
        db,
        page_index=page_index or 1,
        page_size=page_size  or 40,
    )


@router.get("/GetProductColor")
def get_product_colors(db: Session = Depends(get_db)):
    rows = db.execute(sqlalchemy.text(
        'SELECT DISTINCT "Color" FROM twam."ProductVariants" '
        'WHERE "DeletedInd"=false AND "Color" IS NOT NULL ORDER BY "Color"'
    )).fetchall()
    return [r[0] for r in rows]


@router.get("/ProductDetail/{pvd_id}", response_model=schemas.UserProductDetailResponse)
def get_user_product_detail(pvd_id: int, db: Session = Depends(get_db)):
    result = repository.get_user_product_detail(db, pvd_id)
    if not result: raise HTTPException(404, "Product variant detail not found.")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN endpoints — require login — defined AFTER all specific public routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=schemas.ProductVariantDetailListResponse,
            dependencies=[Depends(get_current_user)])
def get_variant_details(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index"),
    Page_Size: Optional[int] = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db)
):
    return repository.get_all_variant_details(
        db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size
    )


@router.post("", status_code=201, dependencies=[Depends(get_current_user)])
def create_variant_detail(command: schemas.ProductVariantDetailCreate, db: Session = Depends(get_db)):
    return {"productVariantDetailId": repository.create_variant_detail(db, command)}


@router.post("/CheckValidations", response_model=schemas.CheckVariantDetailResponse,
             dependencies=[Depends(get_current_user)])
def check_validations(command: schemas.CheckVariantDetailRequest, db: Session = Depends(get_db)):
    count = repository.check_duplicate(
        db, command.productId, command.productVariantId,
        command.sizeId, command.cupSizeId, command.productVariantDetailId or 0
    )
    return {"validationCount": count}


@router.put("/{pvd_id}", dependencies=[Depends(get_current_user)])
def update_variant_detail(pvd_id: int, command: schemas.ProductVariantDetailUpdate, db: Session = Depends(get_db)):
    result = repository.update_variant_detail(db, pvd_id, command)
    if not result: raise HTTPException(404, "ProductVariantDetail not found.")
    return {"productVariantDetailId": result}


@router.delete("/{pvd_id}", status_code=204, dependencies=[Depends(get_current_user)])
def delete_variant_detail(pvd_id: int, db: Session = Depends(get_db)):
    if not repository.delete_variant_detail(db, pvd_id):
        raise HTTPException(404, "ProductVariantDetail not found.")


# /{pvd_id} MUST be last — it's a catch-all for any integer path segment
@router.get("/{pvd_id}", response_model=schemas.ProductVariantDetailResponse,
            dependencies=[Depends(get_current_user)])
def get_variant_detail(pvd_id: int, db: Session = Depends(get_db)):
    result = repository.get_variant_detail_by_id(db, pvd_id)
    if not result: raise HTTPException(404, "ProductVariantDetail not found.")
    return result