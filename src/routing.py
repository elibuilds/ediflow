from typing import Any, TypedDict


class InventoryRoute(TypedDict):
    pantry_items: list[dict[str, Any]]
    flash_sale_items: list[dict[str, Any]]
    excluded_items: list[dict[str, Any]]


def classify_inventory(inventory: list[dict[str, Any]]) -> InventoryRoute:
    """Apply EdiFlow's expiry policy without relying on model classification."""
    if not isinstance(inventory, list):
        raise ValueError("inventory must be a list")

    route: InventoryRoute = {
        "pantry_items": [],
        "flash_sale_items": [],
        "excluded_items": [],
    }
    for item in inventory:
        try:
            days_remaining = item["expires_in_days"]
        except (KeyError, TypeError) as exc:
            raise ValueError("each inventory item needs expires_in_days") from exc
        if not isinstance(days_remaining, int) or isinstance(days_remaining, bool):
            raise ValueError("expires_in_days must be an integer")
        if days_remaining < 0:
            raise ValueError("expires_in_days must be non-negative")

        if days_remaining <= 5:
            route["pantry_items"].append(item)
        elif days_remaining <= 10:
            route["flash_sale_items"].append(item)
        else:
            route["excluded_items"].append(item)
    return route
