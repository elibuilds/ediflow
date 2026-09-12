#defined tools for agent calling
import json
import uuid
from strands import tool

@tool
def fetch_ims_short_dated_inventory(store_id: str, days_threshold: int = 10) -> str:
    """
    Connects to the store's POS/IMS backend (e.g., Shopify, Square, Odoo API)
    and fetches all registered SKUs with expiration dates within the specified threshold.
    """
    if not store_id.strip():
        raise ValueError("store_id must not be empty")
    if days_threshold < 0:
        raise ValueError("days_threshold must be non-negative")

    # Simulated POS/IMS batch payload from local store database
    mock_ims_data = {
        "store_id": store_id,
        "store_name": "Corner Market - Main St.",
        "location": {"lat": 5.6037, "lng": -0.1870},
        "inventory": [
            {
                "sku": "DAIRY-MILK-1L",
                "name": "Fresh Whole Milk 1L",
                "quantity": 24,
                "expires_in_days": 5,
                "refrigeration_required": True,
                "unit_price_usd": 2.50
            },
            {
                "sku": "BAKERY-BREAD-01",
                "name": "Artisanal Wheat Loaf",
                "quantity": 15,
                "expires_in_days": 8,
                "refrigeration_required": False,
                "unit_price_usd": 3.00
            },
            {
                "sku": "PRODUCE-APPLES-BAG",
                "name": "Red Apples 1kg Bag",
                "quantity": 10,
                "expires_in_days": 4,
                "refrigeration_required": False,
                "unit_price_usd": 4.00
            }
        ]
    }
    mock_ims_data["inventory"] = [
        item
        for item in mock_ims_data["inventory"]
        if item["expires_in_days"] <= days_threshold
    ]
    return json.dumps(mock_ims_data)


@tool
def publish_flash_sale(store_id: str, items_json: str) -> str:
    """Publishes a local flash-sale listing for items expiring in 6-10 days."""
    if not store_id.strip():
        raise ValueError("store_id must not be empty")
    items = json.loads(items_json)
    if not isinstance(items, list) or not items:
        raise ValueError("items_json must contain a non-empty item list")
    if any(
        item.get("expires_in_days") is None
        or not 6 <= item["expires_in_days"] <= 10
        for item in items
    ):
        raise ValueError("flash-sale items must expire in 6 to 10 days")

    listings = []
    for item in items:
        days_remaining = item["expires_in_days"]
        discount_percent = 50 + round((10 - days_remaining) * (20 / 4))
        listings.append(
            {
                "listing_id": f"SALE-{uuid.uuid4().hex[:12].upper()}",
                "sku": item.get("sku"),
                "name": item["name"],
                "quantity": item["quantity"],
                "original_unit_price_usd": item.get("unit_price_usd"),
                "discount_percent": discount_percent,
                "sale_unit_price_usd": round(
                    item["unit_price_usd"] * (1 - discount_percent / 100), 2
                ),
                "expires_in_days": days_remaining,
                "status": "PUBLISHED",
            }
        )
    return json.dumps({"store_id": store_id, "listings": listings})

@tool
def check_pantry_capacity_and_match(items_json: str) -> str:
    """
    Evaluates perishable donation items against registered community pantries,
    checking cold-storage capacity, active operating hours, and urgency.
    """
    payload = json.loads(items_json)
    if isinstance(payload, dict):
        items = payload.get("inventory", [])
        store = payload
    else:
        items = payload
        store = {}
    if not isinstance(items, list) or not items:
        raise ValueError("items_json must contain a non-empty item list")
    
    # Mock registry of local community pantries & cold-storage states
    pantry_registry = [
        {
            "pantry_id": "PANTRY-NORTH-01",
            "name": "Hope Community Shelter & Pantry",
            "fridge_capacity_units": 50,
            "accepts_refrigerated": True,
            "distance_km": 2.4
        },
        {
            "pantry_id": "PANTRY-WEST-02",
            "name": "Grace Table Food Bank",
            "fridge_capacity_units": 10,
            "accepts_refrigerated": True,
            "distance_km": 5.1
        }
    ]
    
    total_units = sum(item.get("quantity", 0) for item in items)
    matching_pantry = next(
        (
            pantry
            for pantry in pantry_registry
            if pantry["fridge_capacity_units"] >= total_units
            and all(
                not item.get("refrigeration_required")
                or pantry["accepts_refrigerated"]
                for item in items
            )
        ),
        None,
    )
    if matching_pantry is None:
        raise ValueError("No pantry has capacity for the requested inventory")

    match_results = {
        "allocated_pantry": matching_pantry,
        "assigned_items": items,
        "store_id": store.get("store_id"),
        "store_name": store.get("store_name", "Unknown store"),
        "pickup_location": store.get("location"),
        "pickup_urgency": "HIGH" if any(i.get("expires_in_days", 5) <= 5 for i in items) else "MEDIUM"
    }
    
    return json.dumps(match_results)

@tool
def dispatch_volunteer_pickup(pantry_match_json: str) -> str:
    """
    Generates dispatch orders, creates an optimal route, and sends SMS/WhatsApp
    notifications to verified local volunteer drivers for physical pickup.
    """
    match = json.loads(pantry_match_json)
    
    assigned_items = match.get("assigned_items", [])
    total_units = sum(item.get("quantity", 0) for item in assigned_items)
    driver = (
        "Volunteer Mark (Vehicle: Van - Tag #2841)"
        if total_units > 10
        else "Volunteer Ama (Vehicle: Hatchback - Tag #7312)"
    )
    dispatch_summary = {
        "status": "DISPATCH_SENT",
        "assigned_driver": driver,
        "store_id": match.get("store_id"),
        "pickup_location": match.get("pickup_location"),
        "dropoff_location": match["allocated_pantry"]["name"],
        "estimated_eta_minutes": round(match["allocated_pantry"]["distance_km"] * 8 + 5),
        "items": assigned_items,
        "confirmation_token": f"EDIFLOW-{uuid.uuid4().hex[:10].upper()}",
    }
    
    return json.dumps(dispatch_summary)