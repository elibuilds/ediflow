import os
import json
import hashlib
import hmac
import logging
import secrets
import threading
import time
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import Dict, Optional
from db import (
    get_store_summary as db_get_store_summary,
    list_flash_sales as db_list_flash_sales,
    reserve_flash_sale as db_reserve_flash_sale,
    record_rescue_run,
    sync_inventory_snapshot,
    get_store_membership,
    get_supabase,
)
from integrations.ims import DemoIMSAdapter
from main import create_ediflow_agent
from routing import classify_inventory
from tools.vision_tool import process_produce_photo_ingestion
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ediflow.server")

app = FastAPI(
    title="EdiFlow Autonomous Rescue Agent API",
    description="Amazon Bedrock AgentCore Runtime endpoint for EdiFlow",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get("EDIFLOW_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Webhook-Timestamp", "X-Webhook-Signature", "Idempotency-Key"],
)

# Initialize agent instance
agent = create_ediflow_agent()

class RescueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: Optional[str] = None


class ReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int
    resident_reference: str


class VisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_base64: str
    media_type: str = "image/jpeg"


_idempotency_results: Dict[str, dict] = {}
_idempotency_in_flight: set[str] = set()
_rate_limit_state: Dict[str, list[float]] = {}
_security_lock = threading.Lock()

async def require_store_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Validate a Supabase access token and resolve its active store membership."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Store login required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Store login required")
    try:
        user_response = get_supabase().auth.get_user(token)
        user = user_response.user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid store session") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Invalid store session")
    membership = get_store_membership(str(user.id))
    if not membership:
        raise HTTPException(status_code=403, detail="No active store membership")
    return {
        "user_id": str(user.id),
        "store_id": membership["store_id"],
        "store_name": (membership.get("stores") or {}).get(
            "name", membership["store_id"]
        ),
        "role": membership["role"],
    }

async def require_request_security(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None),
    x_webhook_timestamp: Optional[str] = Header(default=None),
    x_webhook_signature: Optional[str] = Header(default=None),
) -> None:
    """Authenticate, authorize, verify, and throttle rescue requests."""
    if authorization and authorization.lower().startswith("bearer "):
        request.state.store_user = await require_store_user(authorization)
        body = await request.body()
        request.state.rescue_body = body
        if body not in (b"", b"{}"):
            raise HTTPException(
                status_code=400,
                detail="Authenticated rescue requests must not include store_id",
            )
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(status_code=400, detail="A valid Idempotency-Key is required")
        request.state.idempotency_key = idempotency_key
        with _security_lock:
            now = time.monotonic()
            key = request.state.store_user["user_id"]
            recent_requests = [
                sent_at for sent_at in _rate_limit_state.get(key, [])
                if now - sent_at < 60
            ]
            if len(recent_requests) >= 10:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            recent_requests.append(now)
            _rate_limit_state[key] = recent_requests
        return

    configured_key = os.environ.get("EDIFLOW_API_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Rescue API authentication is not configured",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    allowed_stores = {
        store_id.strip()
        for store_id in os.environ.get("EDIFLOW_ALLOWED_STORE_IDS", "").split(",")
        if store_id.strip()
    }
    if not allowed_stores:
        raise HTTPException(status_code=503, detail="No authorized stores are configured")

    body = await request.body()
    request.state.rescue_body = body
    try:
        requested_store = RescueRequest.model_validate_json(body).store_id
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid rescue request") from exc
    if requested_store not in allowed_stores:
        raise HTTPException(status_code=403, detail="Store is not authorized")

    webhook_secret = os.environ.get("EDIFLOW_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook verification is not configured")
    if not x_webhook_timestamp or not x_webhook_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    try:
        timestamp = int(x_webhook_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook timestamp") from exc
    if abs(time.time() - timestamp) > 300:
        raise HTTPException(status_code=401, detail="Expired webhook signature")
    signed_payload = f"{x_webhook_timestamp}.".encode() + body
    expected_signature = hmac.new(
        webhook_secret.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(x_webhook_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key is required")
    request.state.idempotency_key = idempotency_key
    with _security_lock:
        now = time.monotonic()
        recent_requests = [
            sent_at
            for sent_at in _rate_limit_state.get(x_api_key, [])
            if now - sent_at < 60
        ]
        if len(recent_requests) >= 10:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        recent_requests.append(now)
        _rate_limit_state[x_api_key] = recent_requests

@app.get("/health")
def health_check():
    """Health check endpoint for Bedrock AgentCore Runtime container probes."""
    return {"status": "healthy", "service": "EdiFlow AgentCore", "version": "1.0.0"}


@app.get("/api/v1/me")
def current_store(store_user: dict = Depends(require_store_user)):
    """Return the store resolved from the authenticated Supabase user."""
    return store_user


@app.post("/api/v1/vision/parse")
def parse_store_photo(
    vision_request: VisionRequest,
    store_user: dict = Depends(require_store_user),
):
    """Parse a store photo into candidate inventory items using Bedrock vision."""
    try:
        parsed = process_produce_photo_ingestion(
            store_user["store_id"],
            vision_request.image_base64,
            vision_request.media_type,
        )
        return json.loads(parsed)
    except (ValueError, json.JSONDecodeError) as exc:
        error_id = uuid.uuid4().hex
        logger.warning("Vision photo parsing failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=422,
            detail={"message": "Photo could not be parsed", "error_id": error_id},
        ) from exc
    except Exception as exc:
        error_id = uuid.uuid4().hex
        logger.exception("Vision service failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=502,
            detail={"message": "Vision service unavailable", "error_id": error_id},
        ) from exc


@app.get("/api/v1/demo-ims/inventory")
def demo_ims_inventory(store_id: str = "STORE-ACCRA-01", days_threshold: int = 10):
    """Expose the deterministic demo IMS payload for integration demonstrations."""
    if days_threshold < 0 or days_threshold > 30:
        raise HTTPException(status_code=400, detail="days_threshold must be between 0 and 30")
    try:
        snapshot = DemoIMSAdapter().fetch_inventory(store_id, days_threshold)
        return snapshot.__dict__
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/flash-sales")
def list_flash_sales(store_id: Optional[str] = None):
    """List currently published neighborhood flash-sale inventory."""
    try:
        return {"listings": db_list_flash_sales(store_id)}
    except Exception as exc:
        error_id = uuid.uuid4().hex
        logger.exception("Flash-sale listing lookup failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=503,
            detail={"message": "Flash-sale service unavailable", "error_id": error_id},
        ) from exc


@app.post("/api/v1/flash-sales/{listing_id}/reservations")
def reserve_flash_sale(listing_id: str, reservation: ReservationRequest):
    """Atomically reserve available flash-sale inventory for a resident."""
    if reservation.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    if not reservation.resident_reference.strip():
        raise HTTPException(status_code=400, detail="resident_reference is required")

    try:
        return db_reserve_flash_sale(
            listing_id, reservation.quantity, reservation.resident_reference
        )
    except Exception as exc:
        message = str(exc)
        if "Not enough inventory" in message:
            raise HTTPException(status_code=409, detail=message) from exc
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=500, detail="Reservation failed") from exc


@app.get("/api/v1/stores/{store_id}/summary")
def store_summary(store_id: str, store_user: dict = Depends(require_store_user)):
    """Return the store metrics needed by the store-owner workspace."""
    if store_id != store_user["store_id"]:
        raise HTTPException(status_code=403, detail="Store is not authorized")
    try:
        return db_get_store_summary(store_id)
    except Exception as exc:
        error_id = uuid.uuid4().hex
        logger.exception("Store summary lookup failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=503,
            detail={"message": "Store summary unavailable", "error_id": error_id},
        ) from exc

@app.post("/api/v1/trigger-rescue", dependencies=[Depends(require_request_security)])
async def trigger_rescue_cycle(request: Request):
    """
    Trigger an autonomous food rescue cycle for a given local store.
    Called via store IMS webhooks, cron timers, or frontend dashboard.
    """
    body = request.state.rescue_body
    rescue_request = RescueRequest.model_validate_json(body)
    store_id = request.state.store_user["store_id"] if hasattr(
        request.state, "store_user"
    ) else rescue_request.store_id
    if not store_id:
        raise HTTPException(status_code=400, detail="store_id is required")
    idempotency_key = request.state.idempotency_key
    with _security_lock:
        if idempotency_key in _idempotency_results:
            return _idempotency_results[idempotency_key]
        if idempotency_key in _idempotency_in_flight:
            raise HTTPException(status_code=409, detail="Request is already in progress")
        _idempotency_in_flight.add(idempotency_key)

    try:
        snapshot = DemoIMSAdapter().fetch_inventory(store_id, 10)
        route = classify_inventory(snapshot.inventory)
        sync_inventory_snapshot(snapshot.__dict__)
    except Exception as exc:
        error_id = uuid.uuid4().hex
        logger.exception("IMS synchronization failed", extra={"error_id": error_id})
        with _security_lock:
            _idempotency_in_flight.discard(idempotency_key)
        raise HTTPException(
            status_code=502,
            detail={"message": "Inventory synchronization failed", "error_id": error_id},
        ) from exc

    instruction = (
        f"Process short-dated inventory for store {store_id} "
        "and execute the provided deterministic rescue plan. "
        f"Pantry items (0-5 days): {route['pantry_items']}. "
        f"Flash-sale items (6-10 days): {route['flash_sale_items']}. "
        f"Excluded items (>10 days): {route['excluded_items']}. "
        "Do not move items between these categories."
    )
    try:
        response = agent(instruction)
    except Exception as exc:
        with _security_lock:
            _idempotency_in_flight.discard(idempotency_key)
        error_id = uuid.uuid4().hex
        logger.exception("Agent execution failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=500,
            detail={"message": "Agent execution failed", "error_id": error_id},
        ) from exc

    agent_output = str(response)
    failed_output_markers = (
        "i'm sorry",
        "i am sorry",
        "encountering an issue",
        "tool call failed",
        "unable to process",
        "constraint violation",
        "the error persists",
        "failed due to",
        "publishing failed",
        "matching failed",
        "report these issues",
        "technical team",
        "bypass",
    )
    if any(marker in agent_output.lower() for marker in failed_output_markers):
        with _security_lock:
            _idempotency_in_flight.discard(idempotency_key)
        error_id = uuid.uuid4().hex
        logger.error(
            "Agent returned a failure response",
            extra={"error_id": error_id, "agent_output": agent_output},
        )
        raise HTTPException(
            status_code=502,
            detail={"message": "Rescue actions could not be completed", "error_id": error_id},
        )

    result = {
        "status": "SUCCESS",
        "store_id": store_id,
        "agent_output": agent_output,
    }
    try:
        record_rescue_run(
            store_id, idempotency_key, result["agent_output"]
        )
    except Exception as exc:
        with _security_lock:
            _idempotency_in_flight.discard(idempotency_key)
        error_id = uuid.uuid4().hex
        logger.exception("Rescue run persistence failed", extra={"error_id": error_id})
        raise HTTPException(
            status_code=503,
            detail={"message": "Rescue result could not be persisted", "error_id": error_id},
        ) from exc
    with _security_lock:
        _idempotency_in_flight.discard(idempotency_key)
        _idempotency_results[idempotency_key] = result
    return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)