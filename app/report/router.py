import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from . import schemas, repository
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser

router = APIRouter(
    dependencies=[Depends(get_current_user)],prefix="/api/Report", tags=["Report"])

def _paging(Page_Index, Page_Size, Filters):
    return json.loads(Filters) if Filters else None, Page_Index, Page_Size

@router.get("/OrderList", response_model=schemas.ReportListResponse)
def order_list(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_order_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/ProductsCategoryList", response_model=schemas.ReportListResponse)
def products_category_list(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_products_category_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/SalesByRegionReport", response_model=schemas.ReportListResponse)
def sales_by_region(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_sales_by_region(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/TopLowSellingReport", response_model=schemas.ReportListResponse)
def top_low_selling(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_top_low_selling(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/ProductsCategoryReport", response_model=schemas.ReportListResponse)
def products_category_report(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_products_category_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/SalesbyPlatform", response_model=schemas.ReportListResponse)
def sales_by_platform(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_sales_by_platform(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/CouponUsageReport", response_model=schemas.ReportListResponse)
def coupon_usage(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_coupon_usage_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/InvoiceReport", response_model=schemas.ReportListResponse)
def invoice_report(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_invoice_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/GSTReportList", response_model=schemas.ReportListResponse)
def gst_report(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_gst_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/NetVsRevenueReport", response_model=schemas.ReportListResponse)
def net_vs_revenue(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_net_vs_revenue_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/OrderSummary", response_model=schemas.ReportListResponse)
def order_summary(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_order_summary(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/OrderShippingStatus", response_model=schemas.ReportListResponse)
def order_shipping_status(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_order_shipping_status(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/AverageOrderValue", response_model=schemas.ReportListResponse)
def average_order_value(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_average_order_value(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/OrderFulfillment", response_model=schemas.ReportListResponse)
def order_fulfillment(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_order_fulfillment(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/StockBackOrder", response_model=schemas.ReportListResponse)
def stock_back_order(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_stock_back_order(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/PaymentMethodUsage", response_model=schemas.ReportListResponse)
def payment_method_usage(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_payment_method_usage(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/ReturnRateReason", response_model=schemas.ReportListResponse)
def return_rate_reason(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_return_rate_reason(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/FailedPaymentReport", response_model=schemas.ReportListResponse)
def failed_payment(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_failed_payment_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/TaxByRegionReport", response_model=schemas.ReportListResponse)
def tax_by_region(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_tax_by_region(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/StockLevelReport", response_model=schemas.ReportListResponse)
def stock_level(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_stock_level_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/InventoryAgingReport", response_model=schemas.ReportListResponse)
def inventory_aging(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_inventory_aging_report(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/FastSlowMovingInventoryReport", response_model=schemas.ReportListResponse)
def fast_slow_moving(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_fast_slow_moving_inventory(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/ProductReturnRateReport", response_model=schemas.ReportListResponse)
def product_return_rate(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_product_return_rate(db, *_paging(Page_Index, Page_Size, Filters))

@router.get("/StockReorderAlertsReport", response_model=schemas.ReportListResponse)
def stock_reorder_alerts(Filters: Optional[str]=Query(None,alias="Filters"),
    Page_Index: Optional[int]=Query(None,alias="Page.Index",ge=1),
    Page_Size: Optional[int]=Query(None,alias="Page.Size",ge=1), db: Session=Depends(get_db)):
    return repository.get_stock_reorder_alerts(db, *_paging(Page_Index, Page_Size, Filters))