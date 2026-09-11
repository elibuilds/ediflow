import os
from strands import Agent
from tools.core_tools import (
    fetch_ims_short_dated_inventory,
    check_pantry_capacity_and_match,
    dispatch_volunteer_pickup
)

SYSTEM_PROMPT = """
You are EdiFlow, an autonomous hyper-local food rescue agent.
Your objective is to eliminate food waste at local stores while supporting local food banks and residents.

Rules for Execution:
1. Always pull short-dated inventory from the store's IMS first.
2. For items with Expiration <= 2 days: Route immediately to a local pantry with matching cold-storage capacity, and trigger volunteer dispatch.
3. For items with Expiration between 3-5 days: Flag them for a Community Micro-Discount Flash Sale (50-70% off) to benefit local budget shoppers.
4. Run silently: Execute actions via tools and summarize the final dispatch state cleanly without unnecessary conversational fluff.
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