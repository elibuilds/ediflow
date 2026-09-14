import base64
import json
import os
import boto3
from strands import tool

@tool
def process_produce_photo_ingestion(
    store_id: str, image_base64: str, media_type: str = "image/jpeg"
) -> str:
    """
    Uses an image-capable Amazon Bedrock model through the Converse API to identify
    unpackaged or unindexed food items (e.g., bakery trays, fresh fruit crates).
    """
    if not store_id.strip():
        raise ValueError("store_id must not be empty")
    if not image_base64:
        raise ValueError("image_base64 must not be empty")

    allowed_media_types = {"image/jpeg", "image/png", "image/webp"}
    if media_type not in allowed_media_types:
        raise ValueError("media_type must be image/jpeg, image/png, or image/webp")

    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("image_base64 must contain valid base64 data") from exc
    max_image_bytes = int(os.getenv("EDIFLOW_MAX_IMAGE_BYTES", "5242880"))
    if len(image_bytes) > max_image_bytes:
        raise ValueError("image exceeds the configured size limit")

    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv(
        "EDIFLOW_VISION_MODEL_ID",
        os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
    )
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
    
    prompt = """
    Analyze this image from a local grocery store/bakery.
    Identify all visible food items, estimate their quantities, and judge their overall freshness condition.
    Respond strictly in JSON format with keys: store_id, parsed_items (list of objects with name, quantity, estimated_shelf_life_hours).
    """
    
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": media_type.removeprefix("image/"),
                            "source": {"bytes": image_bytes},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
        inferenceConfig={"maxTokens": 1000},
    )

    try:
        model_text = response["output"]["message"]["content"][0]["text"]
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