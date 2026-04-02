from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from .schemas import (
    GridParameters, OrderItemCreate, OrderItemUpdate, OrderItemGrid, OrderItemResponse
)

# ──────────────────────────────────────────────────────────────────────────────
# Whitelist for filter / order fields
# ──────────────────────────────────────────────────────────────────────────────

ALLOWED_FILTER_FIELDS = {
    "OrderItemId":            'oi."OrderItemId"',
    "OrderId":                'oi."OrderId"',
    "ProductId":              'oi."ProductId"',
    "ProductVariantId":       'oi."ProductVariantId"',
    "ProductVariantDetailId": 'oi."ProductVariantDetailId"',
    "OrderItemNumber":        'oi."OrderItemNumber"',
    "TrackingId":             'oi."TrackingId"',
    "Quantity":               'oi."Quantity"',
    "Price":                  'oi."Price"',
    "IsReturn":               'oi."IsReturn"',
    "product_name":           'p."Name"',
    "size_label":             's."SizeLabel"',
    "cup_size_label":         'cs."SizeLabel"',
    "color":                  'pv."Color"',
}

OPERATOR_MAP = {
    "eq":       "=",
    "neq":      "!=",
    "gt":       ">",
    "gte":      ">=",
    "lt":       "<",
    "lte":      "<=",
    "contains": "ILIKE",
}

# ── BUG FIX: was twam."Product" (singular) — correct table is twam."Products" ──
BASE_SELECT = """
        SELECT
            oi."OrderItemId",
            oi."OrderId",
            oi."ProductVariantDetailId",
            oi."ProductId",
            oi."ProductVariantId",
            oi."OrderItemNumber",
            oi."TrackingId",
            oi."Quantity",
            oi."Price",
            oi."TaxAmount",
            oi."UnitPrice",
            oi."CGST",
            oi."SGST",
            oi."Reason",
            oi."IsReturn",
            oi."ReferenceOrderItemId",
            oi."DeletedInd",
            oi."CreatedDate",
            oi."ModifiedDate",
            p."Name"                AS product_name,
            pv."VariantName"        AS variant_name,
            pv."Color"              AS color,
            pv."IsReturnAvailable"  AS is_return_available,
            s."SizeLabel"           AS size_label,
            cs."SizeLabel"          AS cup_size_label,
            (
                SELECT pi2."FilePath"
                FROM twam."ProductImage" pi2
                WHERE pi2."ProductVariantId" = oi."ProductVariantId"
                  AND pi2."DeletedInd" = false
                  AND pi2."FilePath" IS NOT NULL
                  AND pi2."FilePath" != ''
                LIMIT 1
            ) AS "Image"
        FROM twam."OrderItems" oi
        LEFT JOIN twam."Products"             p   ON p."ProductId"               = oi."ProductId"
        LEFT JOIN twam."ProductVariants"       pv  ON pv."ProductVariantId"       = oi."ProductVariantId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId"= oi."ProductVariantDetailId"
        LEFT JOIN mdm."Size"                  s   ON s."SizeId"                  = pvd."Size"
        LEFT JOIN mdm."CupSize"               cs  ON cs."CupSizeId"              = pvd."CupSize"
"""


def _build_where_clause(filters: list) -> tuple:
    conditions = ['oi."DeletedInd" = false']
    params: dict = {}
    if filters:
        for i, f in enumerate(filters):
            col = ALLOWED_FILTER_FIELDS.get(f.field)
            op  = OPERATOR_MAP.get(f.operator, "=")
            if not col or f.value is None:
                continue
            key = f"filter_{i}"
            params[key] = f"%{f.value}%" if op == "ILIKE" else f.value
            conditions.append(f"{col} {op} :{key}")
    return "WHERE " + " AND ".join(conditions), params


def _build_order_clause(order) -> str:
    if not order or not order.field:
        return 'ORDER BY oi."OrderItemId" DESC'
    col = ALLOWED_FILTER_FIELDS.get(order.field)
    if not col:
        return 'ORDER BY oi."OrderItemId" DESC'
    direction = "DESC" if str(order.direction).lower() == "desc" else "ASC"
    return f"ORDER BY {col} {direction}"


def get_order_items_grid(db: Session, grid: GridParameters) -> OrderItemGrid:
    page_number = (grid.page.pageNumber or 1)  if grid.page else 1
    page_size   = (grid.page.pageSize   or 10) if grid.page else 10
    offset      = (page_number - 1) * page_size

    where, params = _build_where_clause(grid.filters or [])
    order_clause  = _build_order_clause(grid.order)

    count_sql = f"SELECT COUNT(*) FROM ({BASE_SELECT} {where}) AS sub"
    total: int = db.execute(text(count_sql), params).scalar() or 0

    data_sql = f"{BASE_SELECT} {where} {order_clause} LIMIT :limit OFFSET :offset"
    params["limit"]  = page_size
    params["offset"] = offset

    rows  = db.execute(text(data_sql), params).mappings().all()
    items = [OrderItemResponse(**dict(row)) for row in rows]

    return OrderItemGrid(total=total, page=page_number, page_size=page_size, items=items)


def get_order_item_by_id(db: Session, order_item_id: int) -> Optional[OrderItemResponse]:
    sql = f'{BASE_SELECT} WHERE oi."DeletedInd" = false AND oi."OrderItemId" = :order_item_id LIMIT 1'
    row = db.execute(text(sql), {"order_item_id": order_item_id}).mappings().first()
    return OrderItemResponse(**dict(row)) if row else None


def create_order_item(db: Session, payload: OrderItemCreate) -> OrderItemResponse:
    sql = text("""
        INSERT INTO twam."OrderItems" (
            "OrderId","ProductVariantDetailId","ProductId","ProductVariantId",
            "OrderItemNumber","TrackingId","Quantity","Price",
            "TaxAmount","UnitPrice","CGST","SGST",
            "Reason","IsReturn","ReferenceOrderItemId","DeletedInd","CreatedDate"
        ) VALUES (
            :OrderId,:ProductVariantDetailId,:ProductId,:ProductVariantId,
            :OrderItemNumber,:TrackingId,:Quantity,:Price,
            :TaxAmount,:UnitPrice,:CGST,:SGST,
            :Reason,:IsReturn,:ReferenceOrderItemId,false,NOW()
        ) RETURNING "OrderItemId"
    """)
    new_id = db.execute(sql, payload.model_dump()).scalar()
    db.commit()
    return get_order_item_by_id(db, new_id)


def update_order_item(db: Session, order_item_id: int, payload: OrderItemUpdate) -> Optional[OrderItemResponse]:
    if not get_order_item_by_id(db, order_item_id):
        return None
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return get_order_item_by_id(db, order_item_id)
    set_clauses = ", ".join([f'"{k}" = :{k}' for k in data])
    data["order_item_id"] = order_item_id
    db.execute(
        text(f'UPDATE twam."OrderItems" SET {set_clauses}, "ModifiedDate"=NOW() WHERE "OrderItemId"=:order_item_id AND "DeletedInd"=false'),
        data
    )
    db.commit()
    return get_order_item_by_id(db, order_item_id)


def delete_order_item(db: Session, order_item_id: int) -> bool:
    if not get_order_item_by_id(db, order_item_id):
        return False
    db.execute(
        text('UPDATE twam."OrderItems" SET "DeletedInd"=true,"ModifiedDate"=NOW() WHERE "OrderItemId"=:id'),
        {"id": order_item_id}
    )
    db.commit()
    return True