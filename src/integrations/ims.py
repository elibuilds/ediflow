import json
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class NormalizedInventory:
    store_id: str
    store_name: str
    location: dict[str, float]
    inventory: list[dict[str, Any]]


class IMSAdapter(Protocol):
    def fetch_inventory(
        self, store_id: str, days_threshold: int
    ) -> NormalizedInventory:
        """Fetch and normalize short-dated inventory from a store IMS."""


class DemoIMSAdapter:
    """Deterministic adapter used until a vendor-specific IMS is configured."""

    def fetch_inventory(
        self, store_id: str, days_threshold: int
    ) -> NormalizedInventory:
        if not store_id.strip():
            raise ValueError("store_id must not be empty")
        if days_threshold < 0:
            raise ValueError("days_threshold must be non-negative")
        items = [
            {
                "sku": "DAIRY-MILK-1L",
                "name": "Fresh Whole Milk 1L",
                "quantity": 24,
                "expires_in_days": 5,
                "refrigeration_required": True,
                "unit_price_usd": 2.50,
            },
            {
                "sku": "BAKERY-BREAD-01",
                "name": "Artisanal Wheat Loaf",
                "quantity": 15,
                "expires_in_days": 8,
                "refrigeration_required": False,
                "unit_price_usd": 3.00,
            },
            {
                "sku": "PRODUCE-APPLES-BAG",
                "name": "Red Apples 1kg Bag",
                "quantity": 10,
                "expires_in_days": 4,
                "refrigeration_required": False,
                "unit_price_usd": 4.00,
            },
        ]
        return NormalizedInventory(
            store_id=store_id,
            store_name="Corner Market - Main St.",
            location={"lat": 5.6037, "lng": -0.1870},
            inventory=[
                item for item in items if item["expires_in_days"] <= days_threshold
            ],
        )


def inventory_json(
    adapter: IMSAdapter, store_id: str, days_threshold: int = 10
) -> str:
    return json.dumps(adapter.fetch_inventory(store_id, days_threshold).__dict__)
