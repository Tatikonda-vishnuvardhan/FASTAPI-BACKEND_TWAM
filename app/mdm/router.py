import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from database import get_db

from app.country      import repository as country_repo
from app.state        import repository as state_repo
from app.fabric       import repository as fabric_repo
from app.size         import repository as size_repo
from app.brand        import repository as brand_repo
from app.cupsize      import repository as cupsize_repo
from app.shippingtype import repository as shippingtype_repo
from app.taxhsncode   import repository as taxhsncode_repo
from app.mdm          import repository as mdm_repo

# NO auth on router — MDM is fully public (all endpoints are reference data)
router = APIRouter(prefix="/api/MDM", tags=["MDM"])


def _p(request: Request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size):
    """
    Accept both Angular params (page.index/page.size) and old-style (Page.Index/Page.Size).
    Treat page.size=0 as None (no limit).
    """
    qp = dict(request.query_params)

    # Angular-style
    pi = int(qp["page.index"]) if "page.index" in qp else None
    ps = int(qp["page.size"])  if "page.size"  in qp else None
    op = qp.get("order.property")
    oa = qp.get("order.ascending")

    # Fall back to old-style if Angular params not present
    final_index = (pi if pi and pi > 0 else None) or (Page_Index if Page_Index and Page_Index > 0 else None)
    final_size  = (ps if ps and ps > 0 else None) or (Page_Size  if Page_Size  and Page_Size  > 0 else None)
    final_prop  = op or Order_Property
    final_asc   = (oa.lower() == "true" if oa else None) if oa is not None else Order_Ascending

    filters = json.loads(Filters) if Filters else None
    return (filters, final_asc, final_prop, final_index, final_size)


def _qparams(f):
    return (
        Query(None, alias="Filters"),
        Query(None, alias="Order.Ascending"),
        Query(None, alias="Order.Property"),
        Query(None, alias="Page.Index"),
        Query(None, alias="Page.Size"),
    )


@router.get("/country")
def get_country(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return country_repo.get_all_countries(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/state")
def get_state(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return state_repo.get_all(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/Fabrics")
def get_fabrics(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return fabric_repo.get_all_fabrics(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/Size")
def get_size(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return size_repo.get_all_sizes(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/Brand")
def get_brand(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return brand_repo.get_all_brands(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/BrandProductCount")
def get_brand_product_count(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    filters, o_asc, o_prop, p_index, p_size = _p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size)
    return mdm_repo.get_brand_product_count(db, filters, o_asc, o_prop, p_index, p_size)


@router.get("/CupSize")
def get_cupsize(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return cupsize_repo.get_all_cupsizes(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/ShippingType")
def get_shippingtype(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return shippingtype_repo.get_all(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))


@router.get("/TaxHSNCode")
def get_taxhsncode(
    request: Request,
    Filters:         Optional[str]  = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property:  Optional[str]  = Query(None, alias="Order.Property"),
    Page_Index:      Optional[int]  = Query(None, alias="Page.Index"),
    Page_Size:       Optional[int]  = Query(None, alias="Page.Size"),
    db: Session = Depends(get_db),
):
    return taxhsncode_repo.get_all(db, *_p(request, Filters, Order_Ascending, Order_Property, Page_Index, Page_Size))