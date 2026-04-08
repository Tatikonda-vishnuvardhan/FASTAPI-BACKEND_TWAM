import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser
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
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    filters = parse_filters(Filters) or []
    if current_user.role_id not in Roles.STAFF:
        filters.append({
            "property": "userProfileId",
            "comparison": "eq",
            "value": current_user.user_id,
        })
    return repository.get_order_list(db, filters or None, Order_Ascending, Order_Property, Page_Index, Page_Size)


# FIX: Added role check — previously ANY authenticated user could call this admin endpoint
@router.get("/AdminList", response_model=schemas.AdminOrderListResponse)
def get_admin_order_list(
    Filters: Optional[str] = Query(None, alias="Filters"),
    Order_Ascending: Optional[bool] = Query(None, alias="Order.Ascending"),
    Order_Property: Optional[str] = Query(None, alias="Order.Property"),
    Page_Index: Optional[int] = Query(None, alias="Page.Index", ge=1),
    Page_Size: Optional[int] = Query(None, alias="Page.Size", ge=1),
    db: Session = Depends(get_db),
    # Only staff roles may access the admin order list
    _: CurrentUser = Depends(require_roles(
        Roles.SUPER_ADMIN, Roles.ORDER_MANAGER, Roles.CUSTOMER_SUPPORT,
        Roles.INVENTORY_MANAGER, Roles.PRODUCT_MANAGER,
    )),
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
    db: Session = Depends(get_db),
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
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = repository.get_order_details(db, order_id)
    if result and current_user.role_id not in Roles.STAFF and result.get("userProfileId") != current_user.user_id:
        result = None
    if not result: raise HTTPException(404, "Order not found.")
    return result


@router.post("/CheckoutSummary", response_model=schemas.CheckoutSummaryResponse)
def checkout_summary(
    command: schemas.CheckoutSummaryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return repository.get_checkout_summary(db, current_user.user_id, command)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/", response_model=schemas.OrderResponse, status_code=201)
def create_order(
    order: schemas.CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not order.userProfileId:
        order.userProfileId = current_user.user_id
    try:
        return repository.create_order(db, order)
    except ValueError as e:
        raise HTTPException(400, str(e))


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


# ── PUBLIC overrides ──────────────────────────────────────────────────────────
@router.post("/GuestOrder", response_model=schemas.OrderResponse, status_code=201, dependencies=[])
def guest_order(command: schemas.CreateGuestOrderRequest, db: Session = Depends(get_db)):
    return repository.create_guest_order(db, command)


@router.put("/CheckOutOfStock", response_model=schemas.ValidationResponse, dependencies=[])
def check_out_of_stock(command: schemas.CheckOutOfStockRequest, db: Session = Depends(get_db)):
    variant_ids = list({i.productVariantDetailId for i in (command.orderItems or []) if i.productVariantDetailId})
    return {"outOfStockProducts": repository.check_out_of_stock(db, variant_ids)}


# ── Admin: Update Order Status (FIX: added role check) ───────────────────────
class UpdateOrderStatusRequest(BaseModel):
    orderId: int
    state: str
    trackingId: Optional[str] = None
    deliveryAgent: Optional[str] = None


@router.put("/UpdateStatus",
            dependencies=[Depends(require_roles(
                Roles.SUPER_ADMIN, Roles.ORDER_MANAGER, Roles.CUSTOMER_SUPPORT
            ))])
def update_order_status(
    command: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
):
    result = repository.update_order_status(
        db,
        command.orderId,
        command.state,
        command.trackingId,
        command.deliveryAgent,
    )
    if not result:
        raise HTTPException(404, "Order not found")
    return {"success": True, "orderId": command.orderId, "state": command.state}