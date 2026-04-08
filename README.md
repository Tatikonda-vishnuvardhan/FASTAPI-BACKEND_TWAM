# TWAM Backend

## Ekart Integration Readiness

The backend now includes:

- Forward shipment creation at `/api/Ekart/CreateShipment`
- Return shipment creation at `/api/Ekart/CreateReturnShipment`
- Tracking at `/api/Ekart/Track/{tracking_id}`
- Shipment cancellation at `/api/Ekart/CancelShipment`
- Webhook receiver at `/api/webhooks/ekart`
- Admin readiness check at `/api/Ekart/Readiness`

## What Must Be Configured For Live Ekart

Set these values in `.env`:

- `EKART_API_URL`
- `EKART_API_KEY`
- `EKART_API_SECRET`
- `EKART_SELLER_ID`
- `EKART_PICKUP_ID`
- `EKART_RETURN_ID`
- `EKART_RETURN_NAME`
- `EKART_RETURN_PHONE`
- `EKART_RETURN_ADDRESS_LINE1`
- `EKART_RETURN_CITY`
- `EKART_RETURN_STATE`
- `EKART_RETURN_PINCODE`

Recommended:

- `EKART_WEBHOOK_SECRET`
- `TRACKING_BASE_URL`

## How To Check Readiness

1. Install dependencies with `pip install -r requirements.txt`
2. Fill the Ekart values in `.env`
3. Set `EKART_MOCK_MODE=false`
4. Start the API
5. Call `/api/Ekart/Readiness`

If `ready_for_live` is `true`, the backend side is ready for real Ekart API testing.

## Webhook URL

Register this callback URL in Ekart:

`https://your-domain/api/webhooks/ekart`
