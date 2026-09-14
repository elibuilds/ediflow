import os
import hashlib
import hmac
import logging
import secrets
import threading
import time
import uuid
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from typing import Dict, Optional
from main import create_ediflow_agent

logger = logging.getLogger("ediflow.server")

app = FastAPI(
    title="EdiFlow Autonomous Rescue Agent API",
    description="Amazon Bedrock AgentCore Runtime endpoint for EdiFlow",
    version="1.0.0"
)

# Initialize agent instance
agent = create_ediflow_agent()

class RescueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: str

_idempotency_results: Dict[str, dict] = {}
_idempotency_in_flight: set[str] = set()
_rate_limit_state: Dict[str, list[float]] = {}
_security_lock = threading.Lock()

async def require_request_security(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None),
    x_webhook_timestamp: Optional[str] = Header(default=None),
    x_webhook_signature: Optional[str] = Header(default=None),
) -> None:
    """Authenticate, authorize, verify, and throttle rescue requests."""
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

@app.post("/api/v1/trigger-rescue", dependencies=[Depends(require_request_security)])
async def trigger_rescue_cycle(request: Request):
    """
    Trigger an autonomous food rescue cycle for a given local store.
    Called via store IMS webhooks, cron timers, or frontend dashboard.
    """
    body = request.state.rescue_body
    rescue_request = RescueRequest.model_validate_json(body)
    idempotency_key = request.state.idempotency_key
    with _security_lock:
        if idempotency_key in _idempotency_results:
            return _idempotency_results[idempotency_key]
        if idempotency_key in _idempotency_in_flight:
            raise HTTPException(status_code=409, detail="Request is already in progress")
        _idempotency_in_flight.add(idempotency_key)

    instruction = (
        f"Process short-dated inventory for store {rescue_request.store_id} "
        "and execute necessary rescue actions."
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

    result = {
        "status": "SUCCESS",
        "store_id": rescue_request.store_id,
        "agent_output": str(response),
    }
    with _security_lock:
        _idempotency_in_flight.discard(idempotency_key)
        _idempotency_results[idempotency_key] = result
    return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)