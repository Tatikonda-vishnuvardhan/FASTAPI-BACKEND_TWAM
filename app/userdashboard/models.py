# UserDashboard does not own any database table.
# It aggregates data from:
#   - twam.Cart
#   - twam.Wishlist
#   - twam.ProductVariant
#   - twam.Products
#   - twam.ProductImage
#   - twam.ProductVariantDetail
#   - twam.ProductReview
#
# All queries are performed via raw SQL in repository.py
# to avoid redefining models owned by other modules.