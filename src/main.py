from strands import Agent
from tools.core_tools import (
    fetch_ims_short_dated_inventory,
    publish_flash_sale,
    check_pantry_capacity_and_match,
    dispatch_volunteer_pickup
)
from tools.vision_tool import process_produce_photo_ingestion

SYSTEM_PROMPT = """
You are EdiFlow, an autonomous hyper-local food rescue agent.
Your objective is to eliminate food waste at local stores while supporting local food banks and residents.

Rules for Execution:
1. Pull short-dated inventory from the store's IMS or process visual photo uploads for unpackaged goods.
2. For items with Expiration <= 5 days: Route immediately to a local pantry with matching cold-storage capacity, and trigger volunteer dispatch.
3. For items with Expiration between 10-6 days: Publish them through the flash-sale tool at a 50-70% discount.
4. Run silently: Execute actions via tools and summarize the final dispatch state cleanly.
"""

def create_ediflow_agent() -> Agent:
    """
    Instantiates the EdiFlow Strands Agent with specified tools and bedrock model configuration.
    """
    agent = Agent(
        model="anthropic.claude-3-5-sonnet-20241022-v2:0", # Amazon Bedrock Claude 3.5 Sonnet
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
    user_prompt = "Process short-dated inventory for store STORE-ACCRA-01 and execute necessary rescue actions."
    
    print(f"\nUser Trigger: {user_prompt}\n" + "-"*50)
    response = ediflow(user_prompt)
    print("\n[EdiFlow Execution Result]:")
    print(response)