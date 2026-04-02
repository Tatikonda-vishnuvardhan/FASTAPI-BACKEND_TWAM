import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from app.auth.dependencies import get_current_user, Roles
from . import schemas, repository

router = APIRouter(
    prefix="/api/Orders",
    tags=["Orders"],
    dependencies=[Depends(get_current_user)],
)


def parse_filters(raw):
    if not raw: return None
    try:
        p = json.loads(raw)
        return p if isinstance(p, list) else [p]
    except: raise HTTPException(400, "Invalid Filters format.")


@router.get("/", response_model=schemas.OrderListResponse)
def get_order_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    return repository.get_order_list(db, parse_filters(Filters), Order_Ascending, Order_Property, Page_Index, Page_Size)


@router.get("/AdminList", response_model=schemas.AdminOrderListResponse)
def get_admin_order_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    filters = parse_filters(Filters)
    clean, sd, ed = [], None, None
    if filters:
        for f in filters:
            if f.get("property") == "startDate": sd = f.get("value")
            elif f.get("property") == "endDate": ed = f.get("value")
            else: clean.append(f)
    return repository.get_admin_order_list(db, clean or None, Order_Ascending, Order_Property, Page_Index, Page_Size, sd, ed)


@router.get("/GetReturnOrderItems", response_model=schemas.ReturnOrderItemsResponse)
def get_return_order_items(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db)
):
    filters = parse_filters(Filters)
    order_id, clean = None, []
    if filters:
        for f in filters:
            if f.get("property") in ("orderId", "OrderId"): order_id = int(f.get("value"))
            else: clean.append(f)
    if not order_id: raise HTTPException(400, "orderId filter is required.")
    result = repository.get_return_order_items(db, order_id, clean or None, Order_Ascending, Order_Property, Page_Index, Page_Size)
    if result is None: raise HTTPException(404, "Order not found.")
    return result


@router.get("/{order_id}", response_model=schemas.GetOrderDetailsResponse)
def get_order_details(order_id: int, db: Session = Depends(get_db)):
    result = repository.get_order_details(db, order_id)
    if not result: raise HTTPException(404, "Order not found.")
    return result


@router.post("/", response_model=schemas.OrderResponse, status_code=201)
def create_order(order: schemas.CreateOrderRequest, db: Session = Depends(get_db)):
    return repository.create_order(db, order)


@router.post("/ReOrder")
def reorder(command: schemas.CreateOrderCartRequest, db: Session = Depends(get_db)):
    return {"orderId": repository.reorder_from_cart(db, command.orderId, command.userProfileId or "")}


@router.post("/CancelOrder")
def cancel_order(command: schemas.CancelOrderRequest, db: Session = Depends(get_db)):
    try:
        return {"success": repository.cancel_order(db, command.orderId, command.isRefund, command.reason, command.platform)}
    except ValueError as e:
        raise HTTPException(404, str(e))


class OrderTrackingBody(BaseModel):
    orderId: int

@router.post("/order-tracking", response_model=schemas.OrderTrackingResponse)
def get_order_tracking(command: OrderTrackingBody, db: Session = Depends(get_db)):
    return repository.get_order_tracking(db, command.orderId)


@router.post("/ReturnOrder")
def return_order(command: schemas.CreateReturnOrderRequest, db: Session = Depends(get_db)):
    return {"success": repository.create_return_order(db, command)}


# ── PUBLIC (override router-level auth) ──────────────────────────────────────
@router.post("/GuestOrder", response_model=schemas.OrderResponse, status_code=201,
             dependencies=[])
def guest_order(command: schemas.CreateGuestOrderRequest, db: Session = Depends(get_db)):
    return repository.create_guest_order(db, command)


@router.put("/CheckOutOfStock", response_model=schemas.ValidationResponse,
            dependencies=[])
def check_out_of_stock(command: schemas.CheckOutOfStockRequest, db: Session = Depends(get_db)):
    variant_ids = list({i.productVariantDetailId for i in (command.orderItems or []) if i.productVariantDetailId})
    return {"outOfStockProducts": repository.check_out_of_stock(db, variant_ids)}
