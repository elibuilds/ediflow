import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from main import create_ediflow_agent

app = FastAPI(
    title="EdiFlow Autonomous Rescue Agent API",
    description="Amazon Bedrock AgentCore Runtime endpoint for EdiFlow",
    version="1.0.0"
)

# Initialize agent instance
agent = create_ediflow_agent()

class RescueRequest(BaseModel):
    store_id: str
    custom_instruction: Optional[str] = None

@app.get("/health")
def health_check():
    """Health check endpoint for Bedrock AgentCore Runtime container probes."""
    return {"status": "healthy", "service": "EdiFlow AgentCore", "version": "1.0.0"}

@app.post("/api/v1/trigger-rescue")
async def trigger_rescue_cycle(request: RescueRequest):
    """
    Trigger an autonomous food rescue cycle for a given local store.
    Called via store IMS webhooks, cron timers, or frontend dashboard.
    """
    try:
        instruction = request.custom_instruction or f"Process short-dated inventory for store {request.store_id} and execute necessary rescue actions."
        
        # Execute Strands Agent flow
        response = agent(instruction)
        
        return {
            "status": "SUCCESS",
            "store_id": request.store_id,
            "agent_output": str(response)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)