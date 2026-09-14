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
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "server-only-service-role-key"
$env:BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
.\.venv\Scripts\python.exe -m server
```

### Supabase setup

Create a hosted Supabase project, then apply
[`supabase/migrations/0001_initial_schema.sql`](./supabase/migrations/0001_initial_schema.sql)
using the Supabase SQL editor or the Supabase CLI. Keep the service-role key only in
the FastAPI deployment environment; never expose it to the browser or commit it.
The rescue endpoint synchronizes the normalized IMS snapshot, publishes 6–10 day
items as flash-sale listings, and records completed rescue runs. Reservations use
the `reserve_flash_sale` Postgres function so concurrent requests cannot oversell a
listing.

After the initial schema, apply
[`supabase/migrations/0002_pantry_dispatch.sql`](./supabase/migrations/0002_pantry_dispatch.sql).
It adds database-backed pantry capacity, allocations, volunteers, and dispatch
state, and seeds the local demo pantry and volunteer records.

Apply [`supabase/migrations/0003_store_auth.sql`](./supabase/migrations/0003_store_auth.sql)
to enable store memberships. Configure the client with
`NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Create a user in
the client, then assign that user's UUID to a store in Supabase:

```sql
insert into public.store_memberships (user_id, store_id, role)
values ('AUTH-USER-UUID', 'STORE-ACCRA-01', 'OWNER');
```

Only users with an active membership can access store summaries or trigger a
rescue. The backend resolves the store from the authenticated Supabase user;
the browser cannot choose an arbitrary store ID.

`GET /health` is public. The rescue endpoint requires the signed request
headers described in [docs/api-contracts.md](docs/api-contracts.md).

## Start the client

In a second terminal:

```powershell
Set-Location client
$env:NEXT_PUBLIC_EDIFLOW_BACKEND_URL = "http://127.0.0.1:8080"
$env:EDIFLOW_BACKEND_URL = "http://127.0.0.1:8080"
$env:EDIFLOW_API_KEY = "demo-api-key"
$env:EDIFLOW_WEBHOOK_SECRET = "demo-webhook-secret"
npm install
npm run dev
```

The resident workspace loads flash-sale listings and submits reservations to
the FastAPI backend. The store workspace loads live summary metrics and
triggers the signed rescue endpoint through the Next.js server-side proxy.

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