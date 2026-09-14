import os
import time
from typing import Any
import boto3
from dotenv import load_dotenv

load_dotenv()


DESCRIPTION = "Autonomous Food Rescue & Multi-Pantry Dispatcher for Good Neighbor Track"


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be configured before deployment")
    return value


def _runtime_config() -> dict[str, Any]:
    return {
        "agentRuntimeName": os.getenv(
            "AGENTCORE_RUNTIME_NAME", "ediflow_good_neighbor"
        ),
        "agentRuntimeArtifact": {
            "containerConfiguration": {
                "containerUri": _required_setting("AGENTCORE_CONTAINER_URI")
            }
        },
        "roleArn": _required_setting("AGENTCORE_ROLE_ARN"),
        "networkConfiguration": {
            "networkMode": os.getenv("AGENTCORE_NETWORK_MODE", "PUBLIC")
        },
        "description": DESCRIPTION,
        "protocolConfiguration": {
            "serverProtocol": os.getenv("AGENTCORE_SERVER_PROTOCOL", "HTTP")
        },
    }


def _find_runtime(client: Any, name: str) -> dict[str, Any] | None:
    response = client.list_agent_runtimes()
    for runtime in response.get("agentRuntimes", []):
        if runtime.get("agentRuntimeName") == name:
            return runtime
    return None


def _find_endpoint(client: Any, runtime_id: str, name: str) -> dict[str, Any] | None:
    response = client.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
    for endpoint in response.get("runtimeEndpoints", []):
        if endpoint.get("name", endpoint.get("endpointName")) == name:
            return endpoint
    return None


def _wait_for_runtime_ready(
    client: Any, runtime_id: str, runtime_version: str
) -> None:
    """Wait for the requested runtime version before creating its endpoint."""
    timeout_seconds = int(os.getenv("AGENTCORE_READY_TIMEOUT_SECONDS", "900"))
    poll_seconds = int(os.getenv("AGENTCORE_READY_POLL_SECONDS", "15"))
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        runtime = client.get_agent_runtime(agentRuntimeId=runtime_id)
        status = runtime.get("status", "")
        current_version = runtime.get("agentRuntimeVersion", runtime_version)
        print(
            f"Waiting for AgentCore runtime {runtime_id} "
            f"version {current_version}: {status or 'UNKNOWN'}"
        )
        if current_version == runtime_version and status == "READY":
            return
        if status in {"FAILED", "DELETING", "DELETE_FAILED"}:
            failure_reason = runtime.get("failureReason")
            raise RuntimeError(
                f"AgentCore runtime version {runtime_version} entered {status}"
                + (f": {failure_reason}" if failure_reason else "")
            )
        time.sleep(poll_seconds)

    raise TimeoutError(
        f"AgentCore runtime version {runtime_version} did not become READY "
        f"within {timeout_seconds} seconds"
    )


def deploy_to_agentcore() -> dict[str, str]:
    """Create or update an AgentCore Runtime and its invocation endpoint.

    The container image must already be available in ECR. This function performs
    the AgentCore control-plane operations and returns their resource identifiers.
    """
    region = os.getenv("AWS_REGION", "us-east-1")
    runtime_config = _runtime_config()
    runtime_name = runtime_config["agentRuntimeName"]
    endpoint_name = os.getenv("AGENTCORE_ENDPOINT_NAME", "production")
    client = boto3.client("bedrock-agentcore-control", region_name=region)

    existing_runtime = _find_runtime(client, runtime_name)
    if existing_runtime:
        runtime_id = existing_runtime["agentRuntimeId"]
        runtime = client.update_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeArtifact=runtime_config["agentRuntimeArtifact"],
            roleArn=runtime_config["roleArn"],
            networkConfiguration=runtime_config["networkConfiguration"],
            description=runtime_config["description"],
            protocolConfiguration=runtime_config["protocolConfiguration"],
        )
        action = "updated"
    else:
        runtime = client.create_agent_runtime(**runtime_config)
        runtime_id = runtime["agentRuntimeId"]
        action = "created"

    runtime_version = runtime["agentRuntimeVersion"]
    _wait_for_runtime_ready(client, runtime_id, runtime_version)
    endpoint = _find_endpoint(client, runtime_id, endpoint_name)
    if endpoint:
        endpoint_result = client.update_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            endpointName=endpoint_name,
            agentRuntimeVersion=runtime_version,
        )
        endpoint_arn = endpoint_result["agentRuntimeEndpointArn"]
    else:
        endpoint_result = client.create_agent_runtime_endpoint(
            agentRuntimeId=runtime_id,
            name=endpoint_name,
            agentRuntimeVersion=runtime_version,
        )
        endpoint_arn = endpoint_result["agentRuntimeEndpointArn"]

    result = {
        "region": region,
        "runtime_id": runtime_id,
        "runtime_version": runtime_version,
        "runtime_action": action,
        "endpoint_arn": endpoint_arn,
        "endpoint_name": endpoint_name,
    }
    print(
        f"AgentCore Runtime {action}: {runtime_id} "
        f"(version {runtime_version}); endpoint: {endpoint_name}"
    )
    return result


if __name__ == "__main__":
    deploy_to_agentcore()
