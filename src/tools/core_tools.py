#defined tools for agent calling
import json
from typing import Dict, Any, List
from strands import tool

@tool
def fetch_ims_short_dated_inventory(store_id: str, days_threshold: int = 10) -> str:
    """
    Connects to the store's POS/IMS backend (e.g., Shopify, Square, Odoo API)
    and fetches all registered SKUs with expiration dates within the specified threshold.
    """
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
    return json.dumps(mock_ims_data)

@tool
def check_pantry_capacity_and_match(items_json: str) -> str:
    """
    Evaluates perishable donation items against registered community pantries,
    checking cold-storage capacity, active operating hours, and urgency.
    """
    items = json.loads(items_json)
    
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
    
    match_results = {
        "allocated_pantry": pantry_registry[0],
        "assigned_items": items,
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
    
    dispatch_summary = {
        "status": "DISPATCH_SENT",
        "assigned_driver": "Volunteer Mark (Vehicle: Van - Tag #2841)",
        "pickup_location": "Corner Market - Main St.",
        "dropoff_location": match["allocated_pantry"]["name"],
        "estimated_eta_minutes": 25,
        "confirmation_token": "EDIFLOW-9942"
    }
    
    return json.dumps(dispatch_summary)