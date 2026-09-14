# EdiFlow

EdiFlow is an autonomous food-rescue prototype for local stores. It connects
store inventory, community pantries, volunteers, and residents so short-dated
food can be rescued instead of wasted.

## What the demo does

1. A store owner signs in with Supabase Auth.
2. The backend resolves the owner's store membership and fetches the store's
   normalized IMS inventory.
3. A deterministic policy routes inventory by remaining shelf life:
   - `0–5 days`: pantry donation and volunteer dispatch
   - `6–10 days`: resident flash sale
   - `>10 days`: excluded from the rescue run
4. The Strands agent executes the approved actions through structured tools.
5. Residents browse public listings and reserve available quantities.
6. Store owners can upload a photo of unpackaged goods for Bedrock vision
   parsing and review the detected candidates.

The current demo uses `DemoIMSAdapter` and Supabase-backed demo pantry and
volunteer records. Vendor-specific IMS, pantry, and dispatch providers can be
added behind the interfaces documented in
[docs/api-contracts.md](docs/api-contracts.md).

## Architecture

```text
Residents and store owners
            │
            ▼
Next.js client (Vercel)
            │ HTTPS
            ▼
FastAPI API (Render)
     ┌──────┼──────────┐
     ▼      ▼          ▼
 Supabase  Bedrock   Demo IMS
 Auth/DB   Nova Lite
            │
            ▼
    Strands rescue agent

AWS AgentCore Runtime
    └── deployable ARM64 runtime image from ECR
```

The public FastAPI deployment serves the web application. The AWS AgentCore
Runtime is deployed separately as the autonomous runtime target. The browser
does not call the AgentCore ARN directly.

## Repository layout

- `src/server.py` — FastAPI API and authentication boundaries
- `src/main.py` — Strands agent construction and standalone workflow
- `src/routing.py` — deterministic expiry routing policy
- `src/db.py` — Supabase persistence and repository functions
- `src/integrations/ims.py` — IMS adapter protocol and demo adapter
- `src/tools/core_tools.py` — inventory, flash-sale, pantry, and dispatch tools
- `src/tools/vision_tool.py` — Bedrock multimodal photo parsing
- `src/deploy_agentcore.py` — AgentCore Runtime deployment automation
- `client/` — Next.js public listings and store workspace
- `supabase/migrations/` — database schema and RLS policies
- `docs/api-contracts.md` — API and integration contracts

## Local setup

Use Python 3.13:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a local environment from `.env.example` and keep it untracked. At
minimum, configure:

```text
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=server-only-service-role-key
EDIFLOW_API_KEY=local-only-api-key
EDIFLOW_WEBHOOK_SECRET=local-only-webhook-secret
EDIFLOW_ALLOWED_STORE_IDS=STORE-ACCRA-01
EDIFLOW_ALLOWED_ORIGINS=http://localhost:3000
```

Start the API:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m server
```

The API runs at `http://127.0.0.1:8080`.

Start the client in a second terminal:

```powershell
Set-Location client
npm install
npm run dev
```

The client runs at `http://localhost:3000`.

For the client, copy `client/.env.example` to `client/.env.local` and set:

```text
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_EDIFLOW_BACKEND_URL=http://127.0.0.1:8080
EDIFLOW_BACKEND_URL=http://127.0.0.1:8080
```

Never put the Supabase service-role key, AWS credentials, or webhook secret in
`NEXT_PUBLIC_*` variables.

## Supabase setup

Create a Supabase project and apply these migrations in order:

1. [0001_initial_schema.sql](supabase/migrations/0001_initial_schema.sql)
2. [0002_pantry_dispatch.sql](supabase/migrations/0002_pantry_dispatch.sql)
3. [0003_store_auth.sql](supabase/migrations/0003_store_auth.sql)

Create a user through `/login`, then assign the user to the demo store using
the user's Auth UUID:

```sql
insert into public.store_memberships (user_id, store_id, role)
values ('AUTH-USER-UUID', 'STORE-ACCRA-01', 'OWNER');
```

Only active store members can access store summaries, trigger rescue runs, or
parse store photos. The backend derives the store from the Supabase bearer
token; the browser cannot choose an arbitrary store.

Inventory synchronization only upserts raw `inventory_items`. The agent's
`publish_flash_sale` tool is the sole path that creates
`flash_sale_listings`. Reservations use the `reserve_flash_sale` Postgres
function so concurrent requests cannot oversell a listing.

## Main routes

Public:

- `GET /health`
- `GET /api/v1/flash-sales`
- `POST /api/v1/flash-sales/{listing_id}/reservations`
- `GET /api/v1/demo-ims/inventory`

Authenticated with a Supabase bearer token:

- `GET /api/v1/me`
- `GET /api/v1/stores/{store_id}/summary`
- `POST /api/v1/trigger-rescue`
- `POST /api/v1/vision/parse`

The photo endpoint accepts Base64 JPEG, PNG, or WebP data and returns detected
candidate items. Photo parsing does not automatically write items to IMS
inventory.

External IMS webhook requests use the API key, timestamp, HMAC signature, and
idempotency headers described in
[docs/api-contracts.md](docs/api-contracts.md).

## Deploy the backend to Render

For the submission demo, deploy the repository root as a Docker Web Service.
The root [Dockerfile](Dockerfile) starts FastAPI with `python -m server`,
binds to `0.0.0.0`, and honors the platform-provided `PORT`.

Recommended Render settings:

```text
Runtime: Docker
Root directory: repository root
Health check path: /health
```

Configure these server-side variables in Render:

```text
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
EDIFLOW_VISION_MODEL_ID=amazon.nova-lite-v1:0
EDIFLOW_ALLOWED_STORE_IDS=STORE-ACCRA-01
EDIFLOW_ALLOWED_ORIGINS=https://your-app.vercel.app
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<secret>
AWS_ACCESS_KEY_ID=<Bedrock-only runtime key>
AWS_SECRET_ACCESS_KEY=<Bedrock-only runtime secret>
EDIFLOW_API_KEY=<secret>
EDIFLOW_WEBHOOK_SECRET=<secret>
```

Use a dedicated AWS identity for Render with only the Bedrock permissions
required by the API:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

Do not use the ECR/AgentCore deployment user's access keys in Render.

After deployment, test the service:

```powershell
Invoke-RestMethod "https://your-render-service.onrender.com/health"
```

The free Render plan may sleep after inactivity. Open `/health` before a demo
to wake the service.

## Deploy the frontend to Vercel

Import the repository into Vercel and set the project root to `client`.
Vercel should detect Next.js automatically. Use:

```text
Build command: npm run build
```

Configure:

```text
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<public-anon-key>
NEXT_PUBLIC_EDIFLOW_BACKEND_URL=https://your-render-service.onrender.com
EDIFLOW_BACKEND_URL=https://your-render-service.onrender.com
```

After Vercel provides the production URL, set that exact origin in Render:

```text
EDIFLOW_ALLOWED_ORIGINS=https://your-app.vercel.app
```

In Supabase, set the Vercel URL under **Authentication → URL Configuration**
and add the production redirect URL:

```text
https://your-app.vercel.app/**
```

## Deploy the AgentCore Runtime

The AgentCore image must be ARM64. Build and push it to ECR:

```powershell
docker buildx build `
  --platform linux/arm64 `
  -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/ediflow:latest `
  --push `
  .
```

The local deployment identity needs ECR push permissions, AgentCore control
plane permissions, and `iam:PassRole`. The separate
`EdiFlowAgentCoreRuntime` role needs:

- `ecr:GetAuthorizationToken`
- `ecr:BatchGetImage`
- `ecr:GetDownloadUrlForLayer`
- Bedrock model invocation
- CloudWatch log delivery

Configure and run:

```powershell
$env:AWS_PROFILE = "ediflow"
$env:AWS_REGION = "us-east-1"
$env:AGENTCORE_CONTAINER_URI = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ediflow:latest"
$env:AGENTCORE_ROLE_ARN = "arn:aws:iam::123456789012:role/EdiFlowAgentCoreRuntime"
$env:AGENTCORE_RUNTIME_NAME = "ediflow_good_neighbor"
$env:AGENTCORE_ENDPOINT_NAME = "production"
$env:PYTHONPATH = "src"

.\.venv\Scripts\python.exe .\src\deploy_agentcore.py
```

The deployment script waits for each runtime version to reach `READY` before
creating or updating the endpoint. The default timeout is 15 minutes; set
`AGENTCORE_READY_TIMEOUT_SECONDS` to increase it.

## Validation

Backend compilation:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m compileall -q src
```

Frontend production build:

```powershell
Set-Location client
npm run build
```

## Security and demo limitations

- Keep `.env` and `client/.env.local` out of Git.
- Rotate any credential that is accidentally exposed.
- Use a dedicated, least-privilege AWS identity for each hosted service.
- The demo IMS adapter currently returns deterministic inventory.
- IMS settings are browser preferences; automatic background synchronization is
  not yet implemented.
- Pantry and volunteer integrations are database-backed demo providers.
- In-process idempotency and rate limiting are not suitable for multi-instance
  production deployments.
- Store membership assignment currently requires administrative SQL.
- AgentCore and Render are separate deployments; the web client uses the
  Render REST API.

## License

This repository is a demonstration project for the EdiFlow food-rescue
concept.
