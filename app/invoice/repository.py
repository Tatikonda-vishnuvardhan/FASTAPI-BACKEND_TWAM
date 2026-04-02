import json
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def get_invoice_by_order_id(db: Session, order_id: int) -> Optional[dict]:
    sql = text("""
        SELECT
            o."OrderId",
            o."OrderNumber",
            o."OrderDate",
            inv."InvoiceNumber",
            inv."CreatedDate"                       AS invoice_date,

            -- Supplier info
            NULL                                    AS supplier_address,
            NULL                                    AS supplier_name,
            NULL                                    AS supplier_gst_number,
            NULL                                    AS signature,
            NULL                                    AS pan_no,

            -- Shipping address
            sa."Name"                               AS shipping_name,
            sa."AddressLine"                        AS shipping_address_line,
            sa."City"                               AS shipping_city,
            shp_country."CountryName"               AS shipping_country_name,
            shp_state."StateName"                   AS shipping_state_name,
            sa."PinCode"                            AS shipping_pin_code,
            sa."Phone"                              AS shipping_phone,

            -- Customer
            o."UserProfileId"                       AS customer_id,
            p."EmailId"                             AS email_address,
            o."PaymentMethod",
            NULL                                    AS shipping_type_name,

            -- Billing address
            ba."Name"                               AS billing_name,
            ba."AddressLine"                        AS billing_address_line,
            ba."City"                               AS billing_city,
            bil_country."CountryName"               AS billing_country_name,
            bil_state."StateName"                   AS billing_state_name,
            ba."PinCode"                            AS billing_pin_code,
            ba."Phone"                              AS billing_phone,

            o."TaxAmount",
            o."TotalAmount",
            o."SubTotal",
            o."PaymentTransactionRefNo",

            -- Line items as JSON
            -- ROW_NUMBER() cannot be nested inside json_agg(), so use a subquery
            (
                SELECT json_agg(json_build_object(
                    'sNo',         sub."sNo",
                    'orderItemId', sub."orderItemId",
                    'description', sub."description",
                    'unitPrice',   sub."unitPrice",
                    'quantity',    sub."quantity",
                    'netAmount',   sub."netAmount",
                    'taxRate',     sub."taxRate",
                    'taxType',     sub."taxType",
                    'taxAmount',   sub."taxAmount",
                    'totalAmount', sub."totalAmount"
                ))
                FROM (
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY oi."OrderItemId") AS "sNo",
                        oi."OrderItemId"                              AS "orderItemId",
                        CONCAT(pv."VariantName", ' - ', pvd_s."SizeLabel") AS "description",
                        oi."UnitPrice"                                AS "unitPrice",
                        oi."Quantity"                                 AS "quantity",
                        oi."Price"                                    AS "netAmount",
                        oi."TaxAmount"                                AS "taxRate",
                        'GST'                                         AS "taxType",
                        oi."TaxAmount"                                AS "taxAmount",
                        oi."Price"                                    AS "totalAmount"
                    FROM twam."OrderItems" oi
                    LEFT JOIN twam."ProductVariants"      pv  ON pv."ProductVariantId"        = oi."ProductVariantId"
                    LEFT JOIN twam."ProductVariantDetail" pvd ON pvd."ProductVariantDetailId" = oi."ProductVariantDetailId"
                    LEFT JOIN mdm."Size"                pvd_s ON pvd_s."SizeId"               = pvd."Size"
                    WHERE oi."OrderId" = o."OrderId" AND oi."DeletedInd" = false
                ) sub
            ) AS items_json

        FROM twam."Orders"  o
        LEFT JOIN twam."Invoice"   inv         ON inv."OrderId"           = o."OrderId"
        LEFT JOIN twam."Address"   sa          ON sa."AddressId"          = o."ShippingAddressId"
        LEFT JOIN twam."Address"   ba          ON ba."AddressId"          = o."BillingAddressId"
        LEFT JOIN mdm."Country"    shp_country ON shp_country."CountryId" = sa."CountryId"
        LEFT JOIN mdm."State"      shp_state   ON shp_state."StateId"     = sa."StateId"
        LEFT JOIN mdm."Country"    bil_country ON bil_country."CountryId" = ba."CountryId"
        LEFT JOIN mdm."State"      bil_state   ON bil_state."StateId"     = ba."StateId"
        LEFT JOIN twam."People"    p           ON p."UserProfileId"       = o."UserProfileId"
                                              AND p."DeletedInd"          = false
        WHERE o."OrderId" = :order_id
        LIMIT 1
    """)

    row = db.execute(sql, {"order_id": order_id}).fetchone()
    if not row:
        return None

    items_json = row[32]
    items = []
    if items_json:
        raw = items_json if isinstance(items_json, list) else json.loads(items_json)
        for i, item in enumerate(raw, 1):
            items.append({
                "sNo":         i,
                "orderItemId": item.get("orderItemId"),
                "description": item.get("description"),
                "unitPrice":   float(item["unitPrice"])   if item.get("unitPrice")   else None,
                "quantity":    item.get("quantity"),
                "netAmount":   float(item["netAmount"])   if item.get("netAmount")   else None,
                "taxRate":     float(item["taxRate"])     if item.get("taxRate")     else None,
                "taxType":     item.get("taxType"),
                "taxAmount":   float(item["taxAmount"])   if item.get("taxAmount")   else None,
                "totalAmount": float(item["totalAmount"]) if item.get("totalAmount") else None,
            })

    return {
        "orderId":                 row[0],
        "orderNumber":             row[1],
        "orderDate":               row[2],
        "invoiceNumber":           row[3],
        "createdDate":             row[4],
        "supplierAddress":         row[5],
        "supplierName":            row[6],
        "supplierGSTNumber":       row[7],
        "signature":               row[8],
        "panNo":                   row[9],
        "shippingName":            row[10],
        "shippingAddressLine":     row[11],
        "shippingCity":            row[12],
        "shippingCountryName":     row[13],
        "shippingStateName":       row[14],
        "shippingPinCode":         row[15],
        "shippingPhone":           row[16],
        "customerId":              row[17],
        "emailAddress":            row[18],
        "paymentMethod":           row[19],
        "shippingTypeName":        row[20],
        "billingName":             row[21],
        "billingAddressLine":      row[22],
        "billingCity":             row[23],
        "billingCountryName":      row[24],
        "billingStateName":        row[25],
        "billingPinCode":          row[26],
        "billingPhone":            row[27],
        "taxAmount":               float(row[28]) if row[28] else None,
        "totalAmount":             float(row[29]) if row[29] else None,
        "subTotal":                float(row[30]) if row[30] else None,
        "paymentTransactionRefNo": row[31],
        "itemsModel":              items,
    }