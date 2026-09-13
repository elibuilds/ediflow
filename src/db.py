import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from supabase import Client, create_client


@lru_cache
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(url, key)


def list_flash_sales(store_id: str | None = None) -> list[dict[str, Any]]:
    query = get_supabase().table("flash_sale_listings").select(
        "*, stores(name)"
    ).eq("status", "PUBLISHED")
    if store_id:
        query = query.eq("store_id", store_id)
    rows = query.execute().data
    return [
        {
            "listing_id": row["id"],
            "store_id": row["store_id"],
            "name": row["name"],
            "store": (row.get("stores") or {}).get("name", row["store_id"]),
            "distance": "Nearby",
            "quantity_available": row["quantity_available"],
            "sale_unit_price_usd": float(row["sale_unit_price_usd"]),
            "original_unit_price_usd": float(row["original_unit_price_usd"]),
            "discount_percent": row["discount_percent"],
            "expires_in": row["expires_at"],
        }
        for row in rows
    ]


def reserve_flash_sale(
    listing_id: str, quantity: int, resident_reference: str
) -> dict[str, Any]:
    response = get_supabase().rpc(
        "reserve_flash_sale",
        {
            "requested_listing_id": listing_id,
            "requested_quantity": quantity,
            "requested_resident_reference": resident_reference,
        },
    ).execute()
    return response.data


def get_store_summary(store_id: str) -> dict[str, Any]:
    client = get_supabase()
    listings = client.table("flash_sale_listings").select(
        "quantity_available,status"
    ).eq("store_id", store_id).execute().data
    inventory = client.table("inventory_items").select(
        "quantity"
    ).eq("store_id", store_id).execute().data
    return {
        "store_id": store_id,
        "items_scanned_today": sum(item["quantity"] for item in inventory),
        "items_rescued": 0,
        "items_on_flash_sale": sum(
            item["quantity_available"]
            for item in listings
            if item["status"] == "PUBLISHED"
        ),
    }


def sync_inventory_snapshot(snapshot: dict[str, Any]) -> None:
    """Persist a normalized IMS snapshot and publish its flash-sale items."""
    client = get_supabase()
    store_id = snapshot["store_id"]
    client.table("stores").upsert(
        {
            "id": store_id,
            "name": snapshot["store_name"],
            "latitude": snapshot["location"].get("lat"),
            "longitude": snapshot["location"].get("lng"),
        }
    ).execute()


def record_rescue_run(
    store_id: str, idempotency_key: str, agent_output: str
) -> None:
    get_supabase().table("rescue_runs").upsert(
        {
            "store_id": store_id,
            "idempotency_key": idempotency_key,
            "status": "COMPLETED",
            "agent_output": agent_output,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="idempotency_key",
    ).execute()
    for item in snapshot["inventory"]:
        inventory = client.table("inventory_items").upsert(
            {**item, "store_id": store_id, "source": "ims"},
            on_conflict="store_id,sku",
        ).execute().data[0]
        if 6 <= item["expires_in_days"] <= 10:
            existing = client.table("flash_sale_listings").select("id").eq(
                "store_id", store_id
            ).eq("sku", item["sku"]).eq("status", "PUBLISHED").execute().data
            if not existing:
                discount = 50 + round((10 - item["expires_in_days"]) * 5)
                client.table("flash_sale_listings").insert(
                    {
                        "store_id": store_id,
                        "inventory_item_id": inventory["id"],
                        "sku": item["sku"],
                        "name": item["name"],
                        "quantity_available": item["quantity"],
                        "original_unit_price_usd": item["unit_price_usd"],
                        "sale_unit_price_usd": round(
                            item["unit_price_usd"] * (1 - discount / 100), 2
                        ),
                        "discount_percent": discount,
                        "expires_at": (
                            datetime.now(timezone.utc)
                            + timedelta(days=item["expires_in_days"])
                        ).isoformat(),
                    }
                ).execute()
