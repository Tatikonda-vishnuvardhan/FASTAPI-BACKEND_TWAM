from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, text
from app.shared.filters import apply_filters, apply_ordering, apply_pagination, build_paged_response

from .models import ProductVariantDetail

# ── Helpers ───────────────────────────────────────────────────────────────────

def _enrich(db: Session, pvd: ProductVariantDetail) -> dict:
    """Add sizeLabel and cupSizeLabel via JOIN."""
    size_label     = None
    cup_size_label = None

    if pvd.sizeId:
        r = db.execute(
            text('SELECT "SizeLabel" FROM mdm."Size" WHERE "SizeId"=:id LIMIT 1'),
            {"id": pvd.sizeId}
        ).fetchone()
        size_label = r[0] if r else None

    if pvd.cupSizeId:
        r = db.execute(
            text('SELECT "SizeLabel" FROM mdm."CupSize" WHERE "CupSizeId"=:id LIMIT 1'),
            {"id": pvd.cupSizeId}
        ).fetchone()
        cup_size_label = r[0] if r else None

    return {
        "productVariantDetailId": pvd.productVariantDetailId,
        "productId":              pvd.productId,
        "productVariantId":       pvd.productVariantId,
        "productCode":            pvd.productCode,
        "sizeId":                 pvd.sizeId,
        "sizeLabel":              size_label,
        "stockQuantity":          pvd.stockQuantity,
        "processedQuantity":      pvd.processedQuantity,
        "returnedQuantity":       pvd.returnedQuantity,
        "availableQuantity":      pvd.availableQuantity,
        "amendmentQuantity":      pvd.amendmentQuantity,
        "discountPercent":        pvd.discountPercent,
        "mrpPrice":               float(pvd.mrpPrice)   if pvd.mrpPrice   else None,
        "finalPrice":             float(pvd.finalPrice)  if pvd.finalPrice  else None,
        "taxAmount":              float(pvd.taxAmount)   if pvd.taxAmount   else None,
        "cgst":                   float(pvd.cgst)        if pvd.cgst        else None,
        "sgst":                   float(pvd.sgst)        if pvd.sgst        else None,
        "userProfileId":          pvd.userProfileId,
        "state":                  pvd.state,
        "stockId":                pvd.stockId,
        "cupSizeId":              pvd.cupSizeId,
        "cupSizeLabel":           cup_size_label,
        "isLowStock":             pvd.isLowStock,
        "isOutOfStock":           pvd.isOutOfStock,
        "isAlphabetSize":         pvd.isAlphabetSize,
        "createdDate":            pvd.createdDate,
        "modifiedDate":           pvd.modifiedDate,
    }


# ── Grid / List ───────────────────────────────────────────────────────────────

def get_all_variant_details(
    db: Session,
    filters: Optional[List[dict]] = None,
    order_ascending: Optional[bool] = None,
    order_property: Optional[str] = None,
    page_index: Optional[int] = None,
    page_size: Optional[int] = None,
) -> dict:
    query = db.query(ProductVariantDetail).filter(ProductVariantDetail.deletedInd == False)

    query = apply_filters(query, ProductVariantDetail, filters)

    query = apply_ordering(query, ProductVariantDetail, order_property, order_ascending)

    total = query.count()
    if page_index and page_size:
        query = query.offset((page_index - 1) * page_size).limit(page_size)

    rows = query.all()
    return build_paged_response(total, [_enrich(db, r) for r in rows])


# ── Get by ID ─────────────────────────────────────────────────────────────────

def get_variant_detail_by_id(db: Session, pvd_id: int) -> Optional[dict]:
    pvd = db.query(ProductVariantDetail).filter(
        ProductVariantDetail.productVariantDetailId == pvd_id,
        ProductVariantDetail.deletedInd == False
    ).first()
    if not pvd:
        return None
    return _enrich(db, pvd)


# ── Create ────────────────────────────────────────────────────────────────────

def create_variant_detail(db: Session, data) -> int:
    pvd = ProductVariantDetail(
        productId         = data.productId,
        productVariantId  = data.productVariantId,
        productCode       = data.productCode,
        sizeId            = data.sizeId,
        stockQuantity     = data.stockQuantity,
        processedQuantity = data.processedQuantity,
        returnedQuantity  = data.returnedQuantity,
        availableQuantity = data.availableQuantity,
        discountPercent   = data.discountPercent,
        mrpPrice          = data.mrpPrice,
        finalPrice        = data.finalPrice,
        taxAmount         = data.taxAmount,
        cgst              = data.cgst,
        sgst              = data.sgst,
        userProfileId     = data.userProfileId,
        state             = data.state,
        cupSizeId         = data.cupSizeId,
        stockId           = data.stockId,
        isAlphabetSize    = data.isAlphabetSize,
        isLowStock        = data.isLowStock,
        isOutOfStock      = data.isOutOfStock,
        createdBy         = data.createdBy,
        createdDate       = datetime.now(timezone.utc),
        deletedInd        = False,
    )
    db.add(pvd)
    db.commit()
    db.refresh(pvd)

    try:
        db.execute(
            text("SELECT twam.\"AutoCreateProductAudit\"(:ref_id, :profile)"),
            {"ref_id": pvd.productVariantDetailId, "profile": "ProductVariantDetail"}
        )
        db.commit()
    except Exception:
        pass

    return pvd.productVariantDetailId


# ── Update ────────────────────────────────────────────────────────────────────

def update_variant_detail(db: Session, pvd_id: int, data) -> Optional[int]:
    """
    Mirrors UpdateProductVariantDetailCommandHandler:
    - Updates all stock/price/state fields
    - Calls AutoCreateProductAudit
    - Calls UpdateProductQuantity (amendment logic)
    """
    pvd = db.query(ProductVariantDetail).filter(
        ProductVariantDetail.productVariantDetailId == pvd_id
    ).first()
    if not pvd:
        return None

    # Apply updates — only overwrite if value provided
    update_fields = {
        "productCode": data.productCode,
        "sizeId": data.sizeId,
        "stockQuantity": data.stockQuantity,
        "processedQuantity": data.processedQuantity,
        "returnedQuantity": data.returnedQuantity,
        "discountPercent": data.discountPercent,
        "mrpPrice": data.mrpPrice,
        "finalPrice": data.finalPrice,
        "taxAmount": data.taxAmount,
        "cgst": data.cgst,
        "sgst": data.sgst,
        "state": data.state,
        "cupSizeId": data.cupSizeId,
        "isAlphabetSize": data.isAlphabetSize,
        "isLowStock": data.isLowStock,
        "isOutOfStock": data.isOutOfStock,
        "amendmentQuantity": data.amendmentQuantity,
        "modifiedBy": data.modifiedBy,
    }
    for field, val in update_fields.items():
        if val is not None:
            setattr(pvd, field, val)

    pvd.modifiedDate = datetime.now(timezone.utc)
    db.commit()

    # Audit
    try:
        db.execute(
            text("SELECT twam.\"AutoCreateProductAudit\"(:ref_id, :profile)"),
            {"ref_id": pvd_id, "profile": "ProductVariantDetail"}
        )
        db.commit()
    except Exception:
        pass

    # Stock quantity update (mirrors EXEC twam.UpdateProductQuantity)
    try:
        is_amendment = data.isAmendment or False
        db.execute(
            text('SELECT twam."UpdateProductQuantity"(:pvd_id, :is_amendment)'),
            {"pvd_id": pvd_id, "is_amendment": is_amendment}
        )
        db.commit()
    except Exception:
        pass

    return pvd_id


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_variant_detail(db: Session, pvd_id: int) -> bool:
    pvd = db.query(ProductVariantDetail).filter(
        ProductVariantDetail.productVariantDetailId == pvd_id,
        ProductVariantDetail.deletedInd == False
    ).first()
    if not pvd:
        return False
    pvd.deletedInd   = True
    pvd.modifiedDate = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Duplicate Check (GetCheckProductVariantDetailQuery) ───────────────────────

def check_duplicate(db: Session, product_id: int, product_variant_id: int,
                    size_id: Optional[int], cup_size_id: Optional[int],
                    current_id: int = 0) -> int:
    """
    Returns count of existing records with same product/variant/size/cupsize.
    count > 0 means a duplicate exists (validation fails).
    Mirrors GetCheckProductVariantDetailQueryHandler.
    """
    query = db.query(ProductVariantDetail).filter(
        ProductVariantDetail.productId        == product_id,
        ProductVariantDetail.productVariantId == product_variant_id,
        ProductVariantDetail.sizeId           == size_id,
        ProductVariantDetail.cupSizeId        == cup_size_id,
        ProductVariantDetail.deletedInd       == False
    )
    if current_id > 0:
        query = query.filter(ProductVariantDetail.productVariantDetailId != current_id)
    return query.count()


# ── User product detail (GetUserProductDetailQuery) ───────────────────────────

def get_user_product_detail(db: Session, pvd_id: int) -> Optional[dict]:
    pvd = db.query(ProductVariantDetail).filter(
        ProductVariantDetail.productVariantDetailId == pvd_id,
        ProductVariantDetail.deletedInd == False
    ).first()
    if not pvd:
        return None
    return {
        "productVariantDetailId": pvd.productVariantDetailId,
        "productId":              pvd.productId,
        "productVariantId":       pvd.productVariantId,
        "price":                  float(pvd.finalPrice)    if pvd.finalPrice    else None,
        "originalPrice":          float(pvd.mrpPrice)      if pvd.mrpPrice      else None,
        "discountPercentage":     float(pvd.discountPercent) if pvd.discountPercent else None,
        "stockQuantity":          pvd.availableQuantity,
        "processedQuantity":      pvd.processedQuantity,
    }