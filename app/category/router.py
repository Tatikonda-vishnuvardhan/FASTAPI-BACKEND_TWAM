import re
import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles
from . import schemas, repository

router = APIRouter(prefix="/api/Category", tags=["Category"])


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
# PUBLIC endpoints — MUST be before /{category_id} catch-all
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/GetCategory", response_model=schemas.CategoryMenuResponse)
def get_category_menu(command: schemas.GetCategoryRequest, db: Session = Depends(get_db)):
    return repository.get_category_menu(db)


@router.get("/GetCategoryProductCount", response_model=list)
def get_category_product_counts(db: Session = Depends(get_db)):
    return repository.get_category_product_counts(db)


@router.get("/GetProductDetailCategory", response_model=schemas.CategoryListResponse)
def get_product_detail_categories(
    request: Request,
    # Accept both Angular (page.index) and old-style (Page.Index) params
    page_index:      Optional[int]  = Query(None, alias="page.index"),
    page_size:       Optional[int]  = Query(None, alias="page.size"),
    order_property:  Optional[str]  = Query(None, alias="order.property"),
    order_ascending: Optional[bool] = Query(None, alias="order.ascending"),
    # Old-style fallback
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    db: Session = Depends(get_db)
):
    # Prefer Angular-style params, fall back to old-style
    p_index = (page_index or Page_Index) if ((page_index or Page_Index) or 0) > 0 else None
    p_size  = (page_size  or Page_Size)  if ((page_size  or Page_Size)  or 0) > 0 else None
    o_prop  = order_property or Order_Property
    o_asc   = order_ascending if order_ascending is not None else Order_Ascending

    filters = parse_angular_filters(request) or parse_filters(Filters) or []
    return repository.get_all_categories(db, filters, o_asc, o_prop, p_index, p_size)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN endpoints — role required
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=schemas.CategoryListResponse,
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER, Roles.INVENTORY_MANAGER))])
def get_categories(
    request: Request,
    page_index:      Optional[int]  = Query(None, alias="page.index"),
    page_size:       Optional[int]  = Query(None, alias="page.size"),
    order_property:  Optional[str]  = Query(None, alias="order.property"),
    order_ascending: Optional[bool] = Query(None, alias="order.ascending"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    db: Session = Depends(get_db)
):
    p_index = (page_index or Page_Index) if ((page_index or Page_Index) or 0) > 0 else None
    p_size  = (page_size  or Page_Size)  if ((page_size  or Page_Size)  or 0) > 0 else None
    o_prop  = order_property or Order_Property
    o_asc   = order_ascending if order_ascending is not None else Order_Ascending

    raw_filters = parse_angular_filters(request) or parse_filters(Filters) or []
    only_child = any(
        f.get("property") == "IsSelectCategory" and
        str(f.get("value", "false")).lower() in ("true", "1")
        for f in raw_filters
    )
    return repository.get_all_categories(db, raw_filters, o_asc, o_prop, p_index, p_size, only_child)


@router.post("", status_code=201,
             dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def create_category(command: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return {"categoryId": repository.create_category(db, command)}


@router.put("/{category_id}",
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def update_category(category_id: int, command: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    result = repository.update_category(db, category_id, command)
    if not result: raise HTTPException(404, "Category not found.")
    return {"categoryId": result}


@router.delete("/{category_id}", status_code=204,
               dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    if not repository.delete_category(db, category_id):
        raise HTTPException(404, "Category not found.")


# /{category_id} MUST be last — catch-all for integer path
@router.get("/{category_id}", response_model=schemas.CategoryResponse,
            dependencies=[Depends(require_roles(Roles.SUPER_ADMIN, Roles.PRODUCT_MANAGER))])
def get_category(category_id: int, db: Session = Depends(get_db)):
    result = repository.get_category_by_id(db, category_id)
    if not result: raise HTTPException(404, "Category not found.")
    return result