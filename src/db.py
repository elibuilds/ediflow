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


def get_store_membership(user_id: str) -> dict[str, Any] | None:
    rows = get_supabase().table("store_memberships").select(
        "user_id, store_id, role, status, stores(name)"
    ).eq("user_id", user_id).eq("status", "ACTIVE").limit(1).execute().data
    return rows[0] if rows else None


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


def publish_flash_sale_listings(
    store_id: str, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Persist validated 6–10 day items as published flash-sale listings."""
    client = get_supabase()
    listings: list[dict[str, Any]] = []
    for item in items:
        inventory_rows = client.table("inventory_items").select("id").eq(
            "store_id", store_id
        ).eq("sku", item["sku"]).execute().data
        if not inventory_rows:
            raise ValueError(f"Inventory item {item['sku']} was not synchronized")

        existing = client.table("flash_sale_listings").select("*").eq(
            "store_id", store_id
        ).eq("sku", item["sku"]).eq("status", "PUBLISHED").execute().data
        if existing:
            listings.append(existing[0])
            continue

        days_remaining = item["expires_in_days"]
        discount_percent = 50 + round((10 - days_remaining) * 5)
        listing = client.table("flash_sale_listings").insert(
            {
                "store_id": store_id,
                "inventory_item_id": inventory_rows[0]["id"],
                "sku": item["sku"],
                "name": item["name"],
                "quantity_available": item["quantity"],
                "original_unit_price_usd": item["unit_price_usd"],
                "sale_unit_price_usd": round(
                    item["unit_price_usd"] * (1 - discount_percent / 100), 2
                ),
                "discount_percent": discount_percent,
                "expires_at": (
                    datetime.now(timezone.utc)
                    + timedelta(days=days_remaining)
                ).isoformat(),
            }
        ).execute().data[0]
        listings.append(listing)
    return listings


def match_pantry(
    inventory: list[dict[str, Any]],
    store_id: str | None,
    store_name: str,
    pickup_location: dict[str, float] | None,
) -> dict[str, Any]:
    """Find and persist a capacity-compatible pantry allocation."""
    client = get_supabase()
    total_units = sum(item.get("quantity", 0) for item in inventory)
    needs_refrigeration = any(
        item.get("refrigeration_required", False) for item in inventory
    )
    pantries = client.table("pantries").select("*").eq("active", True).execute().data
    for pantry in sorted(pantries, key=lambda value: value["distance_km"]):
        if needs_refrigeration and not pantry["accepts_refrigerated"]:
            continue
        allocations = client.table("pantry_allocations").select(
            "allocated_units"
        ).eq("pantry_id", pantry["id"]).in_(
            "status", ["ALLOCATED", "PICKUP_PENDING", "IN_TRANSIT"]
        ).execute().data
        used_units = sum(row["allocated_units"] for row in allocations)
        available_units = pantry["capacity_units"] - used_units
        if available_units < total_units:
            continue
        allocation = client.table("pantry_allocations").insert(
            {
                "store_id": store_id,
                "pantry_id": pantry["id"],
                "allocated_units": total_units,
                "inventory": inventory,
                "status": "ALLOCATED",
            }
        ).execute().data[0]
        return {
            "allocation_id": allocation["id"],
            "allocated_pantry": {
                "pantry_id": pantry["id"],
                "name": pantry["name"],
                "fridge_capacity_units": available_units,
                "accepts_refrigerated": pantry["accepts_refrigerated"],
                "distance_km": pantry["distance_km"],
            },
            "assigned_items": inventory,
            "store_id": store_id,
            "store_name": store_name,
            "pickup_location": pickup_location,
            "pickup_urgency": "HIGH",
        }
    raise ValueError("No pantry has capacity for the requested inventory")


def create_volunteer_dispatch(pantry_match: dict[str, Any]) -> dict[str, Any]:
    """Persist a volunteer dispatch offer for a pantry allocation."""
    client = get_supabase()
    volunteers = client.table("volunteers").select("*").eq(
        "active", True
    ).eq("available", True).order("name").limit(1).execute().data
    if not volunteers:
        raise ValueError("No available volunteer can accept this pickup")
    pantry = pantry_match["allocated_pantry"]
    dispatch = client.table("dispatches").insert(
        {
            "allocation_id": pantry_match["allocation_id"],
            "volunteer_id": volunteers[0]["id"],
            "status": "OFFERED",
            "pickup_location": pantry_match.get("pickup_location"),
            "dropoff_location": pantry["name"],
            "estimated_eta_minutes": round(pantry["distance_km"] * 8 + 5),
        }
    ).execute().data[0]
    return {
        "dispatch_id": dispatch["id"],
        "status": dispatch["status"],
        "assigned_driver": volunteers[0]["name"],
        "vehicle": volunteers[0]["vehicle"],
        "store_id": pantry_match.get("store_id"),
        "pickup_location": pantry_match.get("pickup_location"),
        "dropoff_location": pantry["name"],
        "estimated_eta_minutes": dispatch["estimated_eta_minutes"],
        "items": pantry_match.get("assigned_items", []),
        "confirmation_token": dispatch["confirmation_token"],
    }


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
        "items_rescued": _rescued_item_count(client, store_id),
        "items_on_flash_sale": sum(
            item["quantity_available"]
            for item in listings
            if item["status"] == "PUBLISHED"
        ),
    }


def _rescued_item_count(client: Client, store_id: str) -> int:
    rows = client.table("pantry_allocations").select(
        "allocated_units"
    ).eq("store_id", store_id).in_(
        "status", ["ALLOCATED", "PICKUP_PENDING", "IN_TRANSIT", "DELIVERED"]
    ).execute().data
    return sum(row["allocated_units"] for row in rows)


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
