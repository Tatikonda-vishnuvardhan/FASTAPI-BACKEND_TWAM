"""
MDM repository — delegates to individual module repositories.
BrandProductCount is the only query unique to MDM (counts products per brand).
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.brand.models import Brand
from app.products.models import Products


def get_brand_product_count(db: Session, filters, order_ascending, order_property, page_index, page_size):
    try:
        query = (
            db.query(
                Brand.brandId.label("brandId"),
                Brand.brandName.label("brandName"),
                Brand.brandImage.label("brandImage"),
                Brand.brandLogo.label("brandLogo"),
                func.count(Products.productId).label("productCount"),
            )
            .outerjoin(
                Products,
                (Products.brandId == Brand.brandId) & (Products.deletedInd == False),
            )
            .filter(Brand.deletedInd == False)
            .group_by(Brand.brandId, Brand.brandName, Brand.brandImage, Brand.brandLogo)
            .order_by(func.count(Products.productId).desc())
        )

        total = query.count()
        if page_index and page_size:
            query = query.offset((page_index - 1) * page_size).limit(page_size)

        rows = query.all()
        data = [
            {
                "brandId": row.brandId,
                "brandName": row.brandName,
                "brandImage": row.brandImage,
                "brandLogo": row.brandLogo,
                "productCount": row.productCount,
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[MDM/BrandProductCount] {e}")
        data = []
        total = 0
    return {"count": total, "list": data, "parameters": None}
