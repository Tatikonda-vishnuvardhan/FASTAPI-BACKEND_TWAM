# Report module has no own tables.
# All 22 report endpoints aggregate data from existing tables via raw SQL:
#   twam.Orders, twam.OrderItems, twam.Products, twam.ProductVariant,
#   twam.ProductVariantDetail, twam.Invoice, twam.Cart,
#   mdm.Category, mdm.TaxHSNCode, payment.OrderRefund, twam.Coupons