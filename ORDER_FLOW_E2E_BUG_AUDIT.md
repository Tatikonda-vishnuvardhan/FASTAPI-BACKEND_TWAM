# TWAM Backend Order Flow E2E Bug Audit

Date: 2026-04-08
Scope: Product view, wishlist, cart, checkout, address, shipping, payment, order creation, PayG integration, eKart integration, shipment creation, order updates, notifications
Code changes made: None

## Executive Summary

The current backend is not fully ready for a reliable end-to-end order placement flow.

The main blockers are:

1. Order and wishlist ownership checks are incomplete, which allows unsafe cross-user actions.
2. Payment success, shipment creation, and notification timing are not aligned into one true end-to-end automated flow.
3. PayG correlation fields are stored inconsistently, which can break status polling and callback matching.
4. Some flows create or confirm orders too early, including false-positive confirmation notifications.
5. Shipment persistence differs depending on which eKart/shipment endpoint is used, so reporting and tracking can diverge.

## Review Method

The review traced the backend flow across these modules:

- `main.py`
- `app/orders/router.py`
- `app/orders/repository.py`
- `app/orders/models.py`
- `app/payment/router.py`
- `app/payment/payg_client.py`
- `app/ekart/router.py`
- `app/ekart/webhooks.py`
- `app/ekart/client.py`
- `app/ekart/notifications.py`
- `app/shipment/repository.py`
- `app/cart/router.py`
- `app/cart/repository.py`
- `app/wishlist/router.py`
- `app/wishlist/repository.py`
- `app/address/router.py`
- `app/address/repository.py`
- `app/productvariant/router.py`
- `app/productvariant/repository.py`
- `app/notification/router.py`

## End-to-End Readiness Verdict

### Product View

Partially ready.

Public product browsing works, but the backend does not expose a clearly wired user-facing product-detail endpoint from `app/productvariant/repository.py` even though the repository contains `get_user_product_variant()`.

### Wishlist

Not ready for safe production use.

Core create/list/delete functions exist, but access control is weak enough that wishlist data can be exposed or deleted across users.

### Cart

Mostly functional, but not fully hardened.

Basic create/update/delete logic exists and is user-scoped for update/delete, but there is no stock validation during add-to-cart and some assumptions are deferred until checkout/order placement.

### Checkout and Address

Partially ready.

Checkout summary and address ownership checks are present for the normal logged-in flow, but guest flow validation is weaker and order creation still allows invalid combinations.

### Payment

Partially integrated, not fully reliable end-to-end.

PayG order creation and callback handling exist, but callback persistence, polling keys, and notification timing are inconsistent.

### Order Creation

Not fully hardened.

Orders can be created under bad input conditions, and ownership checks around later order operations are incomplete.

### eKart Integration

Present, but not fully end-to-end ready.

eKart shipment creation, tracking, return shipment creation, and webhook handling exist, but the integration is split across multiple paths that do not persist the same data consistently.

### Shipment Creation and Tracking

Partially ready.

There are two shipment creation paths with different persistence behavior, which can make order tracking and shipment reporting inconsistent.

### Notifications

Email/SMS status notifications exist, but notification timing is wrong in important payment states, and the in-app notification module is only a stub.

## Detailed Findings

### Critical

#### 1. Order numbers and order item numbers are collision-prone

Files:

- `app/orders/repository.py`

Evidence:

- `generate_order_number()` returns `ORD` plus a random 4-digit number.
- `generate_order_item_number()` returns `ORDI` plus a random 4-digit number.

Impact:

- Only 9,000 possible values exist for each pattern.
- Production reuse is inevitable.
- Duplicate order numbers can break admin lookup, shipment references, webhook matching, and customer communication.

Relevant code:

- `app/orders/repository.py`: `generate_order_number()`
- `app/orders/repository.py`: `generate_order_item_number()`

#### 2. Order operations do not consistently enforce ownership

Files:

- `app/orders/router.py`
- `app/orders/repository.py`

Evidence:

- `POST /api/Orders` only overwrites `userProfileId` when it is missing.
- `POST /api/Orders/ReOrder` has no authenticated ownership check.
- `POST /api/Orders/CancelOrder` has no authenticated ownership check.
- `POST /api/Orders/order-tracking` has no authenticated ownership check.
- `POST /api/Orders/ReturnOrder` has no authenticated ownership check.

Impact:

- A logged-in user can potentially act on another user's order if they know or guess the order ID.
- This affects reorder, cancellation, tracking, and return creation.

Relevant code:

- `app/orders/router.py`
- `app/orders/repository.py`

#### 3. Wishlist listing and deletion are unsafe across users

Files:

- `app/wishlist/router.py`
- `app/wishlist/repository.py`

Evidence:

- Public wishlist list endpoint accepts raw client filters and does not enforce current-user scoping.
- Repository only filters by `userProfileId` if the client supplies that filter.
- Delete by wishlist ID is not ownership-scoped.
- Delete by variant ID is not ownership-scoped.

Impact:

- Wishlist data exposure across users.
- One user can delete another user's wishlist entries.

Relevant code:

- `app/wishlist/router.py`
- `app/wishlist/repository.py`

### High

#### 4. COD and prepaid flows are not separated correctly

Files:

- `app/orders/repository.py`
- `app/ekart/router.py`

Evidence:

- Order creation always tries to initiate PayG after order creation.
- There is no skip path for COD orders.
- eKart shipment request chooses COD only when `paymentMethod == "COD"`, but the order flow still attempts online payment first.

Impact:

- COD orders still enter the online payment flow.
- COD orders may remain stuck in `Pending`.
- Frontend behavior can become ambiguous because payment URL handling is always attempted.

Relevant code:

- `app/orders/repository.py`
- `app/ekart/router.py`

#### 5. Order confirmation notifications fire before payment success and can fire twice

Files:

- `app/orders/repository.py`
- `app/payment/router.py`
- `app/ekart/notifications.py`

Evidence:

- Order creation sends `send_order_placed_notification()` immediately after order insert.
- Payment callback sends `send_order_placed_notification()` again on successful payment.

Impact:

- Prepaid customers can receive "order confirmed" before payment is actually approved.
- On successful payment they may receive duplicate order placed notifications.

Relevant code:

- `app/orders/repository.py`
- `app/payment/router.py`

#### 6. PayG correlation data is stored inconsistently

Files:

- `app/orders/repository.py`
- `app/payment/router.py`
- `app/payment/payg_client.py`

Evidence:

- Order creation stores PayG `_unique_request_id` inside `paymentTransactionRefNo`.
- Payment callback later overwrites `paymentTransactionRefNo` with PayG's callback `PaymentTransactionRefNo`.
- Status polling later uses `paymentTransactionRefNo` again as `unique_request_id` fallback.

Impact:

- Live status polling can break after callback overwrite.
- Payment detail lookup fallback becomes unreliable.
- Investigation and reconciliation become harder because one column stores two different meanings at different times.

Relevant code:

- `app/orders/repository.py`
- `app/payment/router.py`
- `app/payment/payg_client.py`

#### 7. The payment callback can still report success even if DB update failed

Files:

- `app/payment/router.py`

Evidence:

- After callback DB failure, the code rolls back and logs the error.
- Notification and redirect still proceed using the original PayG success code.

Impact:

- Frontend may show payment success even when the order row was not updated.
- Customer support and admin view can disagree with what the customer sees.

Relevant code:

- `app/payment/router.py`

#### 8. The backend does not provide one true automatic payment-to-shipment pipeline

Files:

- `app/payment/router.py`
- `app/ekart/router.py`
- `app/shipment/repository.py`

Evidence:

- PayG callback updates payment state only.
- Shipment creation is a separate manual/admin step.
- `/api/Ekart/CreateShipment` updates `Orders` only.
- `app/shipment/repository.py` persists `shipment.Shipment`, but the eKart router path does not.

Impact:

- End-to-end order placement is not fully automated.
- Some shipped orders may have no corresponding row in `shipment.Shipment`.
- Reporting and live tracking can diverge depending on which API path was used.

Relevant code:

- `app/payment/router.py`
- `app/ekart/router.py`
- `app/shipment/repository.py`

#### 9. Checkout/order creation contract allows invalid outcomes

Files:

- `app/orders/router.py`
- `app/orders/repository.py`

Evidence:

- Repository can return only `outOfStockProducts`, but route still responds as created order flow.
- If `cartId` and `orderItems` are both missing, the code still inserts an order row.

Impact:

- Empty orders can be created.
- Clients may treat stock-failure responses as successful order creation because the endpoint remains `201`.

Relevant code:

- `app/orders/router.py`
- `app/orders/repository.py`

#### 10. eKart webhook stores external status text in tracking history while order state stores mapped internal status

Files:

- `app/ekart/webhooks.py`
- `app/ekart/schemas.py`

Evidence:

- Order state is updated with mapped internal state.
- `OrderTrackingStatus.status` is stored using raw `payload.status`.

Impact:

- Tracking history mixes internal and external status vocabularies.
- Any reporting or timeline logic expecting one standard status set can become inconsistent.

Relevant code:

- `app/ekart/webhooks.py`
- `app/ekart/schemas.py`

#### 11. Guest PayG phone field is wrong

Files:

- `app/orders/repository.py`

Evidence:

- Guest order stores phone in `phoneNumber`.
- Guest PayG request reads `data.phone`.

Impact:

- Guest payment requests can be sent with a blank or fallback phone number.

Relevant code:

- `app/orders/repository.py`

#### 12. App startup currently depends on `httpx` for payment module import

Files:

- `main.py`
- `app/payment/payg_client.py`
- `requirements.txt`

Evidence:

- `main.py` imports `app.payment.router`.
- `app.payment.router` imports `payg_client`.
- `payg_client` imports `httpx` at module load time.
- In the current checked environment, that import fails because `httpx` is not installed in `venv1`, even though it is listed in `requirements.txt`.

Impact:

- Application startup can fail in any environment where dependency installation is incomplete.

Relevant code:

- `main.py`
- `app/payment/payg_client.py`
- `requirements.txt`

### Medium

#### 13. Notification API is only a stub

Files:

- `app/notification/router.py`

Evidence:

- Notification endpoint always returns an empty list.

Impact:

- There is no real in-app order update notification system yet.
- Only email/SMS side effects exist.

Relevant code:

- `app/notification/router.py`

#### 14. Guest flow shipping validation is weaker than logged-in checkout flow

Files:

- `app/orders/repository.py`

Evidence:

- Logged-in checkout validates shipping eligibility using subtotal.
- Guest flow only auto-fills delivery charge and does not apply the same eligibility checks.

Impact:

- Guest checkout can allow shipping combinations that the logged-in flow blocks.

Relevant code:

- `app/orders/repository.py`

#### 15. `/api/Ekart/CreateShipment` does not create a `shipment.Shipment` row

Files:

- `app/ekart/router.py`
- `app/shipment/repository.py`

Evidence:

- eKart router updates `twam.Orders` and tracking status only.
- Shipment repository persists `shipment.Shipment`.

Impact:

- Shipment reports and live shipment tracking that rely on `shipment.Shipment` can miss orders shipped through the eKart router path.

Relevant code:

- `app/ekart/router.py`
- `app/shipment/repository.py`

#### 16. Product detail support exists in repository but is not clearly exposed in router

Files:

- `app/productvariant/repository.py`
- `app/productvariant/router.py`

Evidence:

- `get_user_product_variant()` exists in repository.
- Router does not clearly expose a dedicated public product-detail endpoint using that response shape.

Impact:

- Product detail behavior may depend on frontend workarounds or another endpoint not covered here.
- User-facing product detail experience may be incomplete at the API layer.

Relevant code:

- `app/productvariant/repository.py`
- `app/productvariant/router.py`

### Low

#### 17. Cart add flow does not validate stock at add-to-cart time

Files:

- `app/cart/repository.py`
- `app/orders/repository.py`

Evidence:

- Cart create increments quantity directly.
- Stock validation is deferred until checkout/order placement.

Impact:

- Users can add unavailable quantities to cart and discover failure late.

Relevant code:

- `app/cart/repository.py`
- `app/orders/repository.py`

#### 18. Return and shipment status vocabulary is not fully normalized across modules

Files:

- `app/orders/repository.py`
- `app/ekart/webhooks.py`
- `app/ekart/notifications.py`

Evidence:

- Internal states include `Pending`, `Confirmed`, `Processing`, `Shipped`, `Out for Delivery`, `Delivered`, `Cancelled`, `Return Initiated`, `Returned`, `Refunded`.
- Tracking rows sometimes store internal states and sometimes external eKart text.

Impact:

- Reporting, filtering, and timeline rendering can become harder to keep consistent.

Relevant code:

- `app/orders/repository.py`
- `app/ekart/webhooks.py`
- `app/ekart/notifications.py`

## Flow-by-Flow Notes

### Product View to Wishlist

Status: Not safe enough for production

Issues:

- Wishlist list is not strictly scoped to current user.
- Wishlist delete endpoints are not ownership-scoped.

### Product View to Cart

Status: Mostly works, but not hardened

Issues:

- No stock check at add-to-cart time.
- Stock failure is deferred to checkout/order creation.

### Checkout and Address

Status: Partially ready

Strengths:

- Logged-in checkout summary validates address ownership.
- Address routes mostly enforce user ownership.

Issues:

- Guest flow does not mirror the same validation quality.
- Order creation still allows empty-order cases.

### Payment

Status: Partially integrated

Strengths:

- PayG order creation exists.
- Callback endpoint exists.
- Status polling exists.

Issues:

- Correlation fields are overloaded.
- Callback success can outpace DB truth.
- Confirmation notifications happen too early and can duplicate.

### Order Creation

Status: Not fully ready

Issues:

- Empty order possibility.
- Stock-failure response shape is mixed into success route.
- Ownership checks for later order actions are incomplete.

### eKart and Shipment

Status: Present but inconsistent

Strengths:

- Shipment create/cancel/track/return endpoints exist.
- Webhook mapping exists.
- Readiness/config endpoints exist.

Issues:

- Shipment persistence differs by endpoint path.
- Payment success does not automatically create shipment.
- Webhook tracking history uses raw external status text.

### Order Update Notifications

Status: Partial

Strengths:

- Email/SMS notification functions exist for major lifecycle states.

Issues:

- Order placed notification timing is incorrect.
- In-app notification module is not implemented.

## Definite Production Blockers

These should be treated as release blockers for full end-to-end order placement:

1. Weak ownership checks on orders and wishlist.
2. Collision-prone order numbering.
3. COD flow still attempting online payment.
4. Payment correlation field misuse.
5. False or duplicate order confirmation notifications.
6. Shipment persistence mismatch between eKart router path and shipment repository path.
7. Empty-order creation possibility.

## Environment Observation

During import validation in the current local environment:

- `app.orders.repository`, `app.ekart.router`, `app.ekart.webhooks`, `app.cart.repository`, and `app.wishlist.repository` imported successfully through the repo venv.
- `main.py` and `app.payment.router` failed because `httpx` was not installed in the active `venv1`.
- `httpx` is declared in `requirements.txt`, so this is an environment/dependency installation issue in the current workspace, but it still blocks payment module startup here.

## Final Verdict

The backend has a strong amount of implementation already in place, but it is not fully ready for a dependable end-to-end customer order flow without further fixes.

The biggest problems are not missing endpoints. They are flow integrity problems:

- wrong data ownership boundaries
- wrong timing of notifications
- inconsistent payment identifiers
- inconsistent shipment persistence
- lack of one true automated payment-to-shipment pipeline

That means the system can appear complete at the API surface level, but still fail in real production behavior under normal user traffic.
