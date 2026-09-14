import os

from strands import Agent
from tools.core_tools import (
    fetch_ims_short_dated_inventory,
    publish_flash_sale,
    check_pantry_capacity_and_match,
    dispatch_volunteer_pickup
)
from tools.vision_tool import process_produce_photo_ingestion
from integrations.ims import DemoIMSAdapter
from routing import classify_inventory

SYSTEM_PROMPT = """
You are EdiFlow, an autonomous hyper-local food rescue agent.
Your objective is to eliminate food waste at local stores while supporting local food banks and residents.

Rules for Execution:
1. Pull short-dated inventory from the store's IMS or process visual photo uploads for unpackaged goods.
2. Follow the deterministic route plan supplied in the request. Never move an item between its assigned route.
3. For pantry items (0-5 days): match a pantry and trigger volunteer dispatch.
4. For flash-sale items (6-10 days): publish them through the flash-sale tool at a 50-70% discount.
5. Do not act on excluded items (>10 days).
6. Pass tool arguments as structured JSON values: use an inventory list for pantry and flash-sale tools, and a structured pantry match for dispatch.
7. Run silently: Execute actions via tools and summarize the final dispatch state cleanly. If a tool fails, report the failure and do not claim success.
"""

def create_ediflow_agent() -> Agent:
    """
    Instantiates the EdiFlow Strands Agent with specified tools and bedrock model configuration.
    """
    agent = Agent(
        model=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            fetch_ims_short_dated_inventory,
            publish_flash_sale,
            process_produce_photo_ingestion,
            check_pantry_capacity_and_match,
            dispatch_volunteer_pickup
        ]
    )
    return agent

if __name__ == "__main__":
    print("Initializing EdiFlow Rescue Agent...")
    ediflow = create_ediflow_agent()
    
    # Run an autonomous food rescue cycle for local store 'STORE-ACCRA-01'
    store_id = "STORE-ACCRA-01"
    snapshot = DemoIMSAdapter().fetch_inventory(store_id, 10)
    route = classify_inventory(snapshot.inventory)
    user_prompt = (
        f"Process short-dated inventory for store {store_id} "
        "using this deterministic rescue plan. "
        f"Pantry items (0-5 days): {route['pantry_items']}. "
        f"Flash-sale items (6-10 days): {route['flash_sale_items']}. "
        f"Excluded items (>10 days): {route['excluded_items']}. "
        "Do not move items between categories."
    )
    
    print(f"\nUser Trigger: {user_prompt}\n" + "-"*50)
    response = ediflow(user_prompt)
    print("\n[EdiFlow Execution Result]:")
    print(response)