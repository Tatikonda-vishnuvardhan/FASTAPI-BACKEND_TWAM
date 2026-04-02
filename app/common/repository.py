from sqlalchemy.orm import Session
from .models import ProductAudit, ProductVariantAudit, ProductVariantDetailAudit


def get_remarks_history(db: Session, data_profile: str, id: int):
    if data_profile.lower() == "product":
        return (
            db.query(ProductAudit)
            .filter(ProductAudit.referenceId == id)
            .order_by(ProductAudit.createdDate.desc())
            .all()
        )

    if data_profile.lower() == "productvariant":
        return (
            db.query(ProductVariantAudit)
            .filter(ProductVariantAudit.referenceId == id)
            .order_by(ProductVariantAudit.createdDate.desc())
            .all()
        )

    if data_profile.lower() == "productvariantdetail":
        return (
            db.query(ProductVariantDetailAudit)
            .filter(ProductVariantDetailAudit.referenceId == id)
            .order_by(ProductVariantDetailAudit.createdDate.desc())
            .all()
        )

    return []