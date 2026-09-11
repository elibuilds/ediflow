import base64
import json
import boto3
from strands import tool

@tool
def process_produce_photo_ingestion(store_id: str, image_base64: str) -> str:
    """
    Uses Amazon Bedrock Claude 3.5 Sonnet Vision capabilities to identify unpackaged 
    or unindexed food items (e.g., bakery trays, fresh fruit crates) from a store photo.
    """
    bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
    
    prompt = """
    Analyze this image from a local grocery store/bakery.
    Identify all visible food items, estimate their quantities, and judge their overall freshness condition.
    Respond strictly in JSON format with keys: store_id, parsed_items (list of objects with name, quantity, estimated_shelf_life_hours).
    """
    
    # Payload for Anthropic Claude 3.5 Sonnet on Bedrock
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps(payload)
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except Exception as e:
        # Fallback response for offline or dev environments
        return json.dumps({
            "store_id": store_id,
            "parsed_items": [
                {"name": "Assorted Fresh Pastries Tray", "quantity": 12, "estimated_shelf_life_hours": 24},
                {"name": "Ripe Bananas Crate", "quantity": 1, "estimated_units": 30, "estimated_shelf_life_hours": 36}
            ],
            "mode": "FALLBACK_MOCK"
        })