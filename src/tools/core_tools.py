#defined tools for agent calling
import json
from typing import Any
from strands import tool
from db import (
    create_volunteer_dispatch,
    match_pantry,
    publish_flash_sale_listings,
)
from integrations.ims import DemoIMSAdapter, inventory_json

@tool
def fetch_ims_short_dated_inventory(store_id: str, days_threshold: int = 10) -> str:
    """
    Connects to the store's POS/IMS backend (e.g., Shopify, Square, Odoo API)
    and fetches all registered SKUs with expiration dates within the specified threshold.
    """
    return inventory_json(DemoIMSAdapter(), store_id, days_threshold)


@tool
def publish_flash_sale(store_id: str, items: list[dict[str, Any]]) -> str:
    """Publishes a local flash-sale listing for items expiring in 6-10 days."""
    if not store_id.strip():
        raise ValueError("store_id must not be empty")
    if not isinstance(items, list) or not items:
        raise ValueError("items must contain a non-empty item list")
    if any(
        item.get("expires_in_days") is None
        or not 6 <= item["expires_in_days"] <= 10
        for item in items
    ):
        raise ValueError("flash-sale items must expire in 6 to 10 days")

    listings = publish_flash_sale_listings(store_id, items)
    return json.dumps({"store_id": store_id, "listings": listings})

@tool
def check_pantry_capacity_and_match(
    inventory: list[dict[str, Any]],
    store_id: str | None = None,
    store_name: str = "Unknown store",
    pickup_location: dict[str, float] | None = None,
) -> str:
    """
    Evaluates perishable donation items against registered community pantries,
    checking cold-storage capacity, active operating hours, and urgency.
    """
    items = inventory
    if not items:
        raise ValueError("inventory must contain a non-empty item list")
    if any(item.get("expires_in_days", 0) > 5 for item in items):
        raise ValueError("pantry inventory must expire in 0 to 5 days")
    
    return json.dumps(match_pantry(items, store_id, store_name, pickup_location))

@tool
def dispatch_volunteer_pickup(pantry_match: dict[str, Any]) -> str:
    """
    Generates dispatch orders, creates an optimal route, and sends SMS/WhatsApp
    notifications to verified local volunteer drivers for physical pickup.
    """
    match = pantry_match
    
    return json.dumps(create_volunteer_dispatch(match))