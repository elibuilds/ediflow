# EdiFlow interface contracts

These contracts define the integration boundary for the end-to-end demo. They
are intentionally transport-oriented so a real POS/IMS adapter, resident
client, pantry, or volunteer provider can replace the demo implementation
without changing the rescue workflow.

## Authentication and signing

There are two supported side-effecting request paths:

1. Authenticated store dashboard requests.
2. External IMS webhook requests.

Store dashboard requests use:

- `Authorization: Bearer <Supabase access token>`.
- `Idempotency-Key`.

The API validates the Supabase user and resolves the store through
`store_memberships`; the browser must not submit an arbitrary `store_id`.

External IMS webhook requests use:

- `X-API-Key`: service credential.
- `X-Webhook-Timestamp`: Unix timestamp in seconds.
- `X-Webhook-Signature`: lowercase hexadecimal HMAC-SHA256.
- `Idempotency-Key`: caller-generated value, reused for retries of one event.

The signature is calculated over the exact request bytes:

```text
HMAC_SHA256(EDIFLOW_WEBHOOK_SECRET, "<timestamp>.<raw-request-body>")
```

Requests older than five minutes, unauthorized stores, invalid signatures, and
duplicate in-flight idempotency keys are rejected.

## Store IMS ingestion

`POST /api/v1/trigger-rescue`

Request:

```json
{
  "store_id": "STORE-ACCRA-01"
}
```

The endpoint returns a stable rescue result:

```json
{
  "status": "SUCCESS",
  "store_id": "STORE-ACCRA-01",
  "agent_output": "..."
}
```

The current demo accepts a normalized trigger rather than vendor-specific
payloads. A future adapter must normalize vendor data into:

```json
{
  "store_id": "STORE-ACCRA-01",
  "store_name": "Corner Market - Main St.",
  "location": {"lat": 5.6037, "lng": -0.187},
  "inventory": [
    {
      "sku": "DAIRY-MILK-1L",
      "name": "Fresh Whole Milk 1L",
      "quantity": 24,
      "expires_in_days": 5,
      "refrigeration_required": true,
      "unit_price_usd": 2.5
    }
  ]
}
```

## Resident flash-sale interface

The resident-facing resource is:

`GET /api/v1/flash-sales?store_id=STORE-ACCRA-01`

Each listing will expose:

```json
{
  "listing_id": "SALE-...",
  "store_id": "STORE-ACCRA-01",
  "sku": "BAKERY-BREAD-01",
  "name": "Artisanal Wheat Loaf",
  "quantity_available": 15,
  "sale_unit_price_usd": 1.2,
  "discount_percent": 60,
  "expires_at": "2026-09-12T18:00:00Z",
  "status": "PUBLISHED"
}
```

Residents reserve through:

`POST /api/v1/flash-sales/{listing_id}/reservations`

```json
{
  "quantity": 2,
  "resident_reference": "demo-resident-01"
}
```

Reservation state is one of `PENDING`, `CONFIRMED`, `FULFILLED`, `EXPIRED`,
or `CANCELLED`. Inventory must be atomically reserved before returning
`CONFIRMED`.

## Store workspace

`GET /api/v1/stores/{store_id}/summary` returns the aggregate metrics used by
the store-owner workspace:

```json
{
  "store_id": "STORE-ACCRA-01",
  "items_scanned_today": 49,
  "items_rescued": 34,
  "items_on_flash_sale": 15
}
```

The store workspace triggers the authenticated rescue endpoint through the
Next.js server-side proxy. Browser clients never receive the service API key
or webhook secret. The signed webhook path remains available for external IMS
systems and scheduled integrations.

## Store photo ingestion

`POST /api/v1/vision/parse`

This authenticated store-owner endpoint accepts a browser-safe Base64 image
and returns candidate items identified by the configured Bedrock vision model.
The store is resolved from the Supabase bearer token; clients do not submit a
store ID.

```json
{
  "image_base64": "<base64 image bytes>",
  "media_type": "image/jpeg"
}
```

Supported media types are `image/jpeg`, `image/png`, and `image/webp`. The
response contains the authenticated store ID and parsed item names,
quantities, and estimated shelf-life hours. Parsed items are candidates for
review and are not automatically written to IMS inventory.

Inventory synchronization only upserts the raw `inventory_items` snapshot.
The authenticated agent's `publish_flash_sale` action is the sole path that
creates `flash_sale_listings`, so failed or unapproved rescue runs do not
publish listings as a synchronization side effect.

## Pantry and volunteer callbacks

Pantry matching consumes normalized inventory and returns an allocation with
capacity, refrigeration compatibility, pickup location, and operating window.
Volunteer dispatch consumes that allocation and returns a dispatch ID with
`OFFERED`, `ACCEPTED`, `EN_ROUTE`, `PICKED_UP`, `DELIVERED`, or `FAILED` state.

These are internal service contracts for the first demo; external adapters
should preserve the same state transitions and IDs.
