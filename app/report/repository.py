from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def _paginate(rows: list, page_index, page_size) -> dict:
    total = len(rows)
    if page_index and page_size:
        start = (page_index - 1) * page_size
        rows = rows[start: start + page_size]
    return {"count": total, "list": rows, "parameters": None}


def _safe(db: Session, sql: str, params: dict = {}):
    try:
        rows = db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        print(f"[Report] Query error: {e}")
        return []


def get_order_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderId", o."CreatedDate" AS "OrderDate",
               p."Name" AS "ProductName", oi."Quantity",
               pvd."FinalPrice" AS "UnitPrice",
               (oi."Quantity" * pvd."FinalPrice") AS "TotalAmount",
               o."PaymentMethod", o."State",
               COUNT(o."OrderId") OVER() AS "TotalOrders",
               SUM(oi."Quantity" * pvd."FinalPrice") OVER() AS "TotalRevenue"
        FROM twam."Orders" o
        LEFT JOIN twam."OrderItems" oi ON oi."OrderId" = o."OrderId" AND oi."DeletedInd"=false
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        WHERE o."DeletedInd"=false
        ORDER BY o."CreatedDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_products_category_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT c."CategoryName", COUNT(p."ProductId") AS "ProductCount",
               SUM(pvd."FinalPrice" * oi."Quantity") AS "TotalRevenue"
        FROM twam."Category" c
        LEFT JOIN twam."Products" p ON p."CategoryId" = c."CategoryId" AND p."DeletedInd"=false
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductId" = p."ProductId" AND pv."DeletedInd"=false
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantId" = pv."ProductVariantId"
        LEFT JOIN twam."OrderItems" oi ON oi."ProductVariantDetailId" = pvd."ProductVariantDetailId" AND oi."DeletedInd"=false
        WHERE c."DeletedInd"=false
        GROUP BY c."CategoryName" ORDER BY "TotalRevenue" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_sales_by_region(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT a."State" AS "Region",
               COUNT(DISTINCT o."OrderId") AS "TotalOrders",
               SUM(o."TotalAmount") AS "TotalRevenue"
        FROM twam."Orders" o
        LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
        WHERE o."DeletedInd"=false
        GROUP BY a."State" ORDER BY "TotalRevenue" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_top_low_selling(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pv."ProductVariantId",
               COALESCE(SUM(oi."Quantity"), 0) AS "TotalSold",
               COALESCE(SUM(oi."Quantity" * pvd."FinalPrice"), 0) AS "TotalRevenue"
        FROM twam."Products" p
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductId" = p."ProductId" AND pv."DeletedInd"=false
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantId" = pv."ProductVariantId"
        LEFT JOIN twam."OrderItems" oi ON oi."ProductVariantDetailId" = pvd."ProductVariantDetailId" AND oi."DeletedInd"=false
        WHERE p."DeletedInd"=false
        GROUP BY p."Name", pv."ProductVariantId"
        ORDER BY "TotalSold" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_sales_by_platform(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderSource" AS "Platform",
               COUNT(o."OrderId") AS "TotalOrders",
               SUM(o."TotalAmount") AS "TotalRevenue"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false
        GROUP BY o."OrderSource" ORDER BY "TotalRevenue" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_coupon_usage_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT c."CouponCode", c."DiscountType", c."DiscountValue",
               COUNT(o."OrderId") AS "TimesUsed",
               SUM(o."DiscountAmount") AS "TotalDiscount"
        FROM twam."Coupons" c
        LEFT JOIN twam."Orders" o ON o."CouponCode" = c."CouponCode" AND o."DeletedInd"=false
        WHERE c."DeletedInd"=false
        GROUP BY c."CouponCode", c."DiscountType", c."DiscountValue"
        ORDER BY "TimesUsed" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_invoice_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT i."InvoiceId", i."InvoiceNumber", i."InvoiceDate",
               o."OrderId", o."TotalAmount", o."State" AS "OrderState",
               i."TaxAmount", i."TotalAmountWithTax"
        FROM twam."Invoice" i
        LEFT JOIN twam."Orders" o ON o."OrderId" = i."OrderId"
        WHERE i."DeletedInd"=false
        ORDER BY i."InvoiceDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_gst_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderId", o."CreatedDate" AS "OrderDate",
               p."Name" AS "ProductName", oi."Quantity",
               pvd."FinalPrice" AS "UnitPrice",
               t."GSTRate", t."HSNCode",
               (pvd."FinalPrice" * t."GSTRate" / 100) AS "GSTAmount",
               (pvd."FinalPrice" + pvd."FinalPrice" * t."GSTRate" / 100) AS "PriceWithGST"
        FROM twam."Orders" o
        LEFT JOIN twam."OrderItems" oi ON oi."OrderId" = o."OrderId" AND oi."DeletedInd"=false
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        LEFT JOIN mdm."TaxHSNCode" t ON t."TaxHSNCodeId" = p."TaxHSNCodeId"
        WHERE o."DeletedInd"=false
        ORDER BY o."CreatedDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_net_vs_revenue_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT DATE_TRUNC('month', o."CreatedDate") AS "Month",
               SUM(o."TotalAmount") AS "GrossRevenue",
               SUM(o."DiscountAmount") AS "TotalDiscount",
               SUM(o."TotalAmount" - COALESCE(o."DiscountAmount",0)) AS "NetRevenue"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false
        GROUP BY DATE_TRUNC('month', o."CreatedDate")
        ORDER BY "Month" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_order_summary(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."State" AS "OrderStatus",
               COUNT(o."OrderId") AS "TotalOrders",
               SUM(o."TotalAmount") AS "TotalRevenue",
               AVG(o."TotalAmount") AS "AvgOrderValue"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false
        GROUP BY o."State" ORDER BY "TotalOrders" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_order_shipping_status(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderId", o."CreatedDate", o."State" AS "OrderState",
               s."TrackingNumber", s."ShipmentStatus", s."CourierName",
               s."EstimatedDeliveryDate"
        FROM twam."Orders" o
        LEFT JOIN shipment."Shipment" s ON s."OrderId" = o."OrderId" AND s."DeletedInd"=false
        WHERE o."DeletedInd"=false ORDER BY o."CreatedDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_average_order_value(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT DATE_TRUNC('month', o."CreatedDate") AS "Month",
               COUNT(o."OrderId") AS "OrderCount",
               AVG(o."TotalAmount") AS "AvgOrderValue",
               SUM(o."TotalAmount") AS "TotalRevenue"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false
        GROUP BY DATE_TRUNC('month', o."CreatedDate")
        ORDER BY "Month" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_order_fulfillment(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderId", o."CreatedDate",
               o."State" AS "OrderState",
               s."ShipmentStatus",
               EXTRACT(EPOCH FROM (s."CreatedDate" - o."CreatedDate"))/3600 AS "FulfillmentHours"
        FROM twam."Orders" o
        LEFT JOIN shipment."Shipment" s ON s."OrderId" = o."OrderId" AND s."DeletedInd"=false
        WHERE o."DeletedInd"=false ORDER BY o."CreatedDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_stock_back_order(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pvd."ProductVariantDetailId",
               pvd."StockQuantity", COUNT(oi."OrderItemId") AS "PendingOrders"
        FROM twam."ProductVariantDetail" pvd
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        LEFT JOIN twam."OrderItems" oi ON oi."ProductVariantDetailId" = pvd."ProductVariantDetailId"
            AND oi."DeletedInd"=false
        WHERE pvd."StockQuantity" = 0 AND pvd."DeletedInd"=false
        GROUP BY p."Name", pvd."ProductVariantDetailId", pvd."StockQuantity"
    """)
    return _paginate(rows, page_index, page_size)


def get_payment_method_usage(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."PaymentMethod",
               COUNT(o."OrderId") AS "TotalOrders",
               SUM(o."TotalAmount") AS "TotalRevenue",
               ROUND(COUNT(o."OrderId") * 100.0 / SUM(COUNT(o."OrderId")) OVER(), 2) AS "UsagePercent"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false AND o."PaymentMethod" IS NOT NULL
        GROUP BY o."PaymentMethod" ORDER BY "TotalOrders" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_return_rate_reason(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT ori."ReturnReason", COUNT(ori."ReturnInfoId") AS "TotalReturns",
               SUM(o."TotalAmount") AS "ReturnValue"
        FROM twam."OrderReturnInfo" ori
        LEFT JOIN twam."Orders" o ON o."OrderId" = ori."OrderId"
        WHERE ori."DeletedInd"=false
        GROUP BY ori."ReturnReason" ORDER BY "TotalReturns" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_failed_payment_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT o."OrderId", o."CreatedDate", o."TotalAmount",
               o."PaymentMethod", o."PaymentStatus", o."State"
        FROM twam."Orders" o
        WHERE o."DeletedInd"=false
          AND o."PaymentStatus" IN ('Failed', 'Pending', 'Cancelled')
        ORDER BY o."CreatedDate" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_tax_by_region(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT a."State" AS "Region",
               SUM(i."TaxAmount") AS "TotalTax",
               COUNT(DISTINCT i."InvoiceId") AS "InvoiceCount"
        FROM twam."Invoice" i
        LEFT JOIN twam."Orders" o ON o."OrderId" = i."OrderId"
        LEFT JOIN twam."Address" a ON a."AddressId" = o."ShippingAddressId"
        WHERE i."DeletedInd"=false
        GROUP BY a."State" ORDER BY "TotalTax" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_stock_level_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pv."VariantName",
               pvd."ProductVariantDetailId", pvd."StockQuantity",
               pvd."FinalPrice", pvd."MRPPrice"
        FROM twam."ProductVariantDetail" pvd
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        WHERE pvd."DeletedInd"=false
        ORDER BY pvd."StockQuantity" ASC
    """)
    return _paginate(rows, page_index, page_size)


def get_inventory_aging_report(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pvd."ProductVariantDetailId",
               pvd."StockQuantity", pvd."CreatedDate" AS "StockAddedDate",
               EXTRACT(DAY FROM NOW() - pvd."CreatedDate") AS "AgeDays"
        FROM twam."ProductVariantDetail" pvd
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        WHERE pvd."DeletedInd"=false AND pvd."StockQuantity" > 0
        ORDER BY "AgeDays" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_fast_slow_moving_inventory(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pvd."ProductVariantDetailId",
               COALESCE(SUM(oi."Quantity"), 0) AS "TotalSold",
               pvd."StockQuantity" AS "CurrentStock",
               CASE WHEN COALESCE(SUM(oi."Quantity"), 0) > 50 THEN 'Fast'
                    WHEN COALESCE(SUM(oi."Quantity"), 0) > 10 THEN 'Medium'
                    ELSE 'Slow' END AS "MovementCategory"
        FROM twam."ProductVariantDetail" pvd
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        LEFT JOIN twam."OrderItems" oi ON oi."ProductVariantDetailId" = pvd."ProductVariantDetailId"
            AND oi."DeletedInd"=false
        WHERE pvd."DeletedInd"=false
        GROUP BY p."Name", pvd."ProductVariantDetailId", pvd."StockQuantity"
        ORDER BY "TotalSold" DESC
    """)
    return _paginate(rows, page_index, page_size)


def get_product_return_rate(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName",
               COUNT(DISTINCT oi."OrderItemId") AS "TotalSold",
               COUNT(DISTINCT ori."ReturnInfoId") AS "TotalReturned",
               ROUND(COUNT(DISTINCT ori."ReturnInfoId") * 100.0 /
                     NULLIF(COUNT(DISTINCT oi."OrderItemId"), 0), 2) AS "ReturnRate"
        FROM twam."Products" p
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductId" = p."ProductId"
        LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantId" = pv."ProductVariantId"
        LEFT JOIN twam."OrderItems" oi ON oi."ProductVariantDetailId" = pvd."ProductVariantDetailId" AND oi."DeletedInd"=false
        LEFT JOIN twam."OrderReturnInfo" ori ON ori."OrderId" = oi."OrderId" AND ori."DeletedInd"=false
        WHERE p."DeletedInd"=false
        GROUP BY p."Name" ORDER BY "ReturnRate" DESC NULLS LAST
    """)
    return _paginate(rows, page_index, page_size)


def get_stock_reorder_alerts(db: Session, filters, page_index, page_size):
    rows = _safe(db, """
        SELECT p."Name" AS "ProductName", pvd."ProductVariantDetailId",
               pvd."StockQuantity",
               pvd."ReorderLevel",
               CASE WHEN pvd."StockQuantity" <= pvd."ReorderLevel" THEN 'REORDER NOW'
                    ELSE 'OK' END AS "AlertStatus"
        FROM twam."ProductVariantDetail" pvd
        LEFT JOIN twam."ProductVariants" pv ON pv."ProductVariantId" = pvd."ProductVariantId"
        LEFT JOIN twam."Products" p ON p."ProductId" = pv."ProductId"
        WHERE pvd."DeletedInd"=false
          AND pvd."ReorderLevel" IS NOT NULL
          AND pvd."StockQuantity" <= pvd."ReorderLevel"
        ORDER BY pvd."StockQuantity" ASC
    """)
    return _paginate(rows, page_index, page_size)