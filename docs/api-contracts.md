# EdiFlow interface contracts

These contracts define the integration boundary for the end-to-end demo. They
are intentionally transport-oriented so a real POS/IMS adapter, resident
client, pantry, or volunteer provider can replace the demo implementation
without changing the rescue workflow.

## Authentication and signing

Side-effecting store requests use:

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

The planned resident-facing resource is:

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

Residents will reserve through:

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

## Pantry and volunteer callbacks

Pantry matching consumes normalized inventory and returns an allocation with
capacity, refrigeration compatibility, pickup location, and operating window.
Volunteer dispatch consumes that allocation and returns a dispatch ID with
`OFFERED`, `ACCEPTED`, `EN_ROUTE`, `PICKED_UP`, `DELIVERED`, or `FAILED` state.

These are internal service contracts for the first demo; external adapters
should preserve the same state transitions and IDs.
