"""
MDM repository — delegates to individual module repositories.
BrandProductCount is the only query unique to MDM (counts products per brand).
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def get_brand_product_count(db: Session, filters, order_ascending, order_property, page_index, page_size):
    try:
        rows = db.execute(text("""
            SELECT b."brandId", b."brandName", b."brandImage", b."brandLogo",
                   COUNT(p."ProductId") AS "productCount"
            FROM   brands b
            LEFT JOIN twam."Products" p ON p."BrandId" = b."brandId" AND p."DeletedInd" = false
            WHERE  b."deletedInd" = false
            GROUP  BY b."brandId", b."brandName", b."brandImage", b."brandLogo"
            ORDER  BY "productCount" DESC
        """)).fetchall()
        data = [dict(r._mapping) for r in rows]
    except Exception as e:
        print(f"[MDM/BrandProductCount] {e}")
        data = []

    total = len(data)
    if page_index and page_size:
        start = (page_index - 1) * page_size
        data = data[start: start + page_size]
    return {"count": total, "list": data, "parameters": None}
