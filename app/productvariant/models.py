from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class ProductVariant(Base):
    """Maps to twam.ProductVariants"""
    __tablename__ = "ProductVariants"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    productVariantId    = Column("ProductVariantId",   BigInteger, primary_key=True, index=True, autoincrement=True)
    productId           = Column("ProductId",           BigInteger, nullable=False)
    variantName         = Column("VariantName",         String,     nullable=True)
    variantDescription  = Column("VariantDescription",  String,     nullable=True)
    userProfileId       = Column("UserProfileId",       String,     nullable=True)
    state               = Column("State",               String,     nullable=True)
    productCode         = Column("ProductCode",         String,     nullable=True)
    fabricId            = Column("FabricId",            BigInteger, nullable=True)
    color               = Column("Color",               String,     nullable=True)
    isBestSeller        = Column("IsBestSeller",        Boolean,    nullable=True)
    taxHSNCodeId        = Column("TaxHSNCodeId",        BigInteger, nullable=True)
    isReturnAvailable   = Column("IsReturnAvailable",   Boolean,    nullable=True)
    isCupSize           = Column("IsCupSize",           Boolean,    nullable=True)
    createdBy           = Column("CreatedBy",           String,     nullable=True)
    modifiedBy          = Column("ModifiedBy",          String,     nullable=True)
    createdDate         = Column("CreatedDate",         DateTime(timezone=True), server_default=func.now())
    modifiedDate        = Column("ModifiedDate",        DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deletedInd          = Column("DeletedInd",          Boolean,    default=False)


class ProductImage(Base):
    """Maps to twam.ProductImage"""
    __tablename__ = "ProductImage"
    __table_args__ = {"schema": "twam", "extend_existing": True}

    productImageId   = Column("ProductImageId",   BigInteger, primary_key=True, index=True, autoincrement=True)
    productId        = Column("ProductId",         BigInteger, nullable=True)
    productVariantId = Column("ProductVariantId",  BigInteger, nullable=True)
    fileName         = Column("FileName",          String,     nullable=True)
    fileType         = Column("FileType",          String,     nullable=True)
    filePath         = Column("FilePath",          String,     nullable=True)
    createdDate      = Column("CreatedDate",       DateTime(timezone=True), server_default=func.now())
    deletedInd       = Column("DeletedInd",        Boolean,    default=False)