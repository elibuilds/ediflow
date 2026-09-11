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
    if not store_id.strip():
        raise ValueError("store_id must not be empty")
    if not image_base64:
        raise ValueError("image_base64 must not be empty")

    try:
        base64.b64decode(image_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("image_base64 must contain valid base64 data") from exc

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
    
    response = bedrock_runtime.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps(payload)
    )
    result = json.loads(response["body"].read())

    try:
        model_text = result["content"][0]["text"]
        parsed_result = json.loads(model_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Bedrock returned an invalid vision response") from exc

    if (
        not isinstance(parsed_result, dict)
        or parsed_result.get("store_id") != store_id
        or not isinstance(parsed_result.get("parsed_items"), list)
    ):
        raise ValueError("Bedrock vision response did not match the required schema")

    return json.dumps(parsed_result)