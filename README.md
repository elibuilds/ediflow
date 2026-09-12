# EdiFlow

EdiFlow is a Strands Agents prototype for rescuing short-dated store inventory.
The target flow is:

1. A store IMS sends a signed rescue trigger.
2. Inventory is classified by remaining shelf life.
3. Items with 0–5 days remaining are matched to a pantry and dispatched.
4. Items with 6–10 days remaining are published as resident flash-sale
   listings.

The integration contracts are documented in
[docs/api-contracts.md](docs/api-contracts.md). The current inventory, pantry,
dispatch, and listing providers are demo adapters; they are designed to be
replaced by real providers behind those contracts.

## Local setup

Use Python 3.13 and install the pinned dependencies:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the API:

```powershell
$env:PYTHONPATH = "src"
$env:EDIFLOW_API_KEY = "demo-api-key"
$env:EDIFLOW_ALLOWED_STORE_IDS = "STORE-ACCRA-01"
$env:EDIFLOW_WEBHOOK_SECRET = "demo-webhook-secret"
.\.venv\Scripts\python.exe -m server
```

`GET /health` is public. The rescue endpoint requires the signed request
headers described in [docs/api-contracts.md](docs/api-contracts.md).

## Deploying the AgentCore Runtime

Build and push the container image to Amazon ECR before running the deployment
script. The deployment script does not guess a repository or push local Docker
images; it deploys the immutable image URI that you provide.

Configure AWS credentials with permission to use the
`bedrock-agentcore-control` API, then set:

```powershell
$env:AWS_REGION = "us-east-1"
$env:AGENTCORE_CONTAINER_URI = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ediflow:latest"
$env:AGENTCORE_ROLE_ARN = "arn:aws:iam::123456789012:role/EdiFlowAgentCoreRuntime"
$env:AGENTCORE_RUNTIME_NAME = "ediflow-good-neighbor"
$env:AGENTCORE_ENDPOINT_NAME = "production"
```

Run the deployment from the repository root:

```powershell
$env:PYTHONPATH = "src"
python src/deploy_agentcore.py
```

The script creates or updates the named AgentCore Runtime and creates or
updates its endpoint. It prints the runtime ID, version, and endpoint ARN only
after the corresponding AWS API calls succeed.