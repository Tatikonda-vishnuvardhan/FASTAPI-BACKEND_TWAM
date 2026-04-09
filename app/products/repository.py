from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import Products
from app.brand.models import Brand

def _to_response(db: Session, product: Products) -> dict:
    """Attach brandName from the Brand ORM model."""
    brand_name = None
    if product.brandId:
        brand = db.query(Brand).filter(
            Brand.brandId == product.brandId,
            Brand.deletedInd == False
        ).first()
        if brand:
            brand_name = brand.brandName
    return {
        "productId":        product.productId,
        "productCode":      product.productCode,
        "name":             product.name,
        "description":      product.description,
        "categoryId":       product.categoryId,
        "childCategoryId":  product.childCategoryId,
        "brandId":          product.brandId,
        "brandName":        brand_name,
        "personalId":       product.personalId,
        "userProfileId":    product.userProfileId,
        "tag":              product.tag,
        "state":            product.state,
        "createdBy":        product.createdBy,
        "modifiedBy":       product.modifiedBy,
        "createdDate":      product.createdDate,
        "modifiedDate":     product.modifiedDate,
    }


def get_all_products(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
) -> dict:
    query = db.query(Products).filter(Products.deletedInd == False)

    query = apply_filters(query, Products, filters)

    query = apply_ordering(query, Products, order_property, order_ascending)

    total = query.count()

    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)

    rows = query.all()
    return {
        "count":      total,
        "list":       [_to_response(db, r) for r in rows],
        "parameters": None,
    }


def get_product_by_id(db: Session, product_id: int) -> Optional[dict]:
    product = db.query(Products).filter(
        Products.productId == product_id,
        Products.deletedInd == False
    ).first()
    if not product:
        return None
    return _to_response(db, product)


def create_product(db: Session, data) -> int:
    product = Products(
        productCode     = data.productCode,
        name            = data.name,
        description     = data.description,
        categoryId      = data.categoryId,
        childCategoryId = data.childCategoryId,
        brandId         = data.brandId,
        personalId      = data.personalId,
        userProfileId   = data.userProfileId,
        state           = data.state,
        tag             = data.tag,
        createdBy       = data.createdBy,
        createdDate     = datetime.now(timezone.utc),
        deletedInd      = False,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Call audit function (PostgreSQL equivalent of EXEC twam.AutoCreateProductAudit)
    try:
        db.execute(
            text("SELECT twam.\"AutoCreateProductAudit\"(:ref_id, :profile)"),
            {"ref_id": product.productId, "profile": "Product"}
        )
        db.commit()
    except Exception:
        pass  # Audit is non-critical

    return product.productId


def update_product(db: Session, product_id: int, data) -> Optional[int]:
    product = db.query(Products).filter(
        Products.productId == product_id,
        Products.deletedInd == False
    ).first()
    if not product:
        return None

    for field in ("productCode", "name", "description", "categoryId",
                  "childCategoryId", "brandId", "personalId",
                  "userProfileId", "state", "tag", "modifiedBy"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(product, field, val)

    product.modifiedDate = datetime.now(timezone.utc)
    db.commit()

    try:
        db.execute(
            text("SELECT twam.\"AutoCreateProductAudit\"(:ref_id, :profile)"),
            {"ref_id": product_id, "profile": "Product"}
        )
        db.commit()
    except Exception:
        pass

    return product_id


def delete_product(db: Session, product_id: int) -> bool:
    product = db.query(Products).filter(
        Products.productId == product_id,
        Products.deletedInd == False
    ).first()
    if not product:
        return False

    product.deletedInd   = True
    product.modifiedDate = datetime.now(timezone.utc)
    db.commit()

    # Cascade soft-delete variants, variant details, images
    try:
        db.execute(text(
            'UPDATE twam."ProductVariants" SET "DeletedInd" = true WHERE "ProductId" = :pid'
        ), {"pid": product_id})
        db.execute(text(
            'UPDATE twam."ProductVariantDetail" SET "DeletedInd" = true WHERE "ProductId" = :pid'
        ), {"pid": product_id})
        db.execute(text(
            'UPDATE twam."ProductImage" SET "DeletedInd" = true WHERE "ProductId" = :pid'
        ), {"pid": product_id})
        db.commit()
    except Exception:
        pass

    return True


def check_product_validations(db: Session, product_id: int, state: Optional[str] = None) -> bool:
    """
    Mirrors GetProductValidationsListQueryHandler:
    - If state == 'Returned For Correction': check if any VariantDetail has ProcessedQuantity > 0
    - Otherwise: check if product has at least 1 variant AND 1 variant detail
    """
    if state == "Returned For Correction":
        count = db.execute(
            text("""
                SELECT COUNT(*) FROM twam."ProductVariantDetail"
                WHERE "DeletedInd" = false
                  AND "ProductId" = :pid
                  AND "ProcessedQuantity" > 0
            """),
            {"pid": product_id}
        ).scalar()
        return (count or 0) > 0

    variant_count = db.execute(
        text('SELECT COUNT(*) FROM twam."ProductVariants" WHERE "DeletedInd" = false AND "ProductId" = :pid'),
        {"pid": product_id}
    ).scalar()
    detail_count = db.execute(
        text('SELECT COUNT(*) FROM twam."ProductVariantDetail" WHERE "DeletedInd" = false AND "ProductId" = :pid'),
        {"pid": product_id}
    ).scalar()
    return (variant_count or 0) > 0 and (detail_count or 0) > 0
