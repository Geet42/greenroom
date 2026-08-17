# Deployment Guide — Azure (Free Tier)

Stack:
- **Frontend** → Azure Static Web Apps (free)
- **Backend (FastAPI)** → Azure Container Apps, consumption plan (free)
- **Piston (code runner)** → Azure Container Apps, consumption plan (free)
- **Database / Auth** → Supabase (keep as-is)

---

## Prerequisites

```bash
# Install Azure CLI if you don't have it
brew install azure-cli        # macOS
# or: winget install Microsoft.AzureCLI

az login
az account set --subscription "<your subscription id>"
```

---

## Step 1 — Create Azure resources (one-time)

```bash
RG="greenroom-rg"
LOCATION="eastus"
ACA_ENV="greenroom-env"

# Resource group
az group create --name $RG --location $LOCATION

# Container Apps environment (this is the "network" your containers share)
az containerappenv create \
  --name $ACA_ENV \
  --resource-group $RG \
  --location $LOCATION

# Backend API container app (starts with a placeholder image; CI will update it)
az containerapp create \
  --name greenroom-api \
  --resource-group $RG \
  --environment $ACA_ENV \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi

# Piston container app (internal — only the API talks to it)
az containerapp create \
  --name greenroom-piston \
  --resource-group $RG \
  --environment $ACA_ENV \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
  --target-port 2000 \
  --ingress internal \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 1.0 \
  --memory 2.0Gi
```

Write down the URL printed for `greenroom-api` — you'll need it in Step 4.

---

## Step 2 — Create a service principal for GitHub Actions

```bash
# Create principal scoped to your resource group
az ad sp create-for-rbac \
  --name "greenroom-github-actions" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/$RG \
  --json-auth
```

This prints a JSON blob. You'll break it into three secrets:
- `clientId` → `AZURE_CLIENT_ID`
- `tenantId` → `AZURE_TENANT_ID`
- `subscriptionId` → `AZURE_SUBSCRIPTION_ID`

Then grant federated identity so OIDC works (no password stored):

```bash
# Replace with your GitHub username and repo name
GITHUB_ORG="VishwajeetRaut"
REPO="greenroom"
APP_ID=$(az ad app list --display-name "greenroom-github-actions" --query '[0].appId' -o tsv)

az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

> **Status check, 2026-08:** this section documents the OIDC setup, but `.github/workflows/deploy-containers.yml` currently authenticates with a single `AZURE_CREDENTIALS` secret (a stored service-principal JSON blob via `az ad sp create-for-rbac --sdk-auth`), not the three `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` secrets this step produces. Either this federated credential was never actually wired into the live workflow, or the workflow regressed back to a stored secret at some point — either way, **confirm before assuming OIDC is active.** Check with `az ad app federated-credential list --id $APP_ID` — if it returns the `github-main` credential above, OIDC is one workflow edit away:
>
> 1. In the repo's GitHub secrets, add `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (from the `az ad sp create-for-rbac` output above) if they aren't already there. You can leave `AZURE_CREDENTIALS` in place for now — it becomes unused, not harmful, until you're ready to delete it.
> 2. In `deploy-containers.yml`, on the `build-and-deploy` job, add `permissions: id-token: write` alongside the existing `contents: read` / `packages: write` (required for the OIDC token exchange).
> 3. Replace the "Log in to Azure" step:
>    ```yaml
>    - name: Log in to Azure
>      uses: azure/login@v2
>      with:
>        client-id: ${{ secrets.AZURE_CLIENT_ID }}
>        tenant-id: ${{ secrets.AZURE_TENANT_ID }}
>        subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
>    ```
>    (drop the `creds:` line entirely — that's what selects password auth over OIDC).
> 4. Push to a branch, run the workflow via `workflow_dispatch` first rather than trusting it on the next real deploy, confirm the Azure login step succeeds.
> 5. Once confirmed working across a couple of runs, delete the `AZURE_CREDENTIALS` secret from the repo and revoke the old service-principal password (`az ad sp credential list` / `az ad sp credential delete` on the same app) so the long-lived credential is actually gone, not just unused.
>
> This is the single biggest gap between this pipeline and a genuinely "industry grade" one — a stored password-style secret has to be manually rotated and can leak in full if the repo or a log line ever exposes it; a federated OIDC token is minted fresh per run and can't be replayed outside that run. Do this migration deliberately, on a day nothing else is riding on the deploy pipeline working — a wrong `client-id` here fails loudly (auth error), but "loudly" during a live demo is still the wrong time to find out.

---

## Step 3 — Create Azure Static Web Apps

Go to https://portal.azure.com → "Static Web Apps" → Create:
- **Resource group**: greenroom-rg
- **Plan**: Free
- **Region**: East US 2
- **Deployment source**: GitHub → your repo → branch: main
- **Build preset**: Vite
- **App location**: `/frontend`
- **Output location**: `dist`

Azure will commit a workflow file to your repo — **delete that file** (we use our own at `.github/workflows/deploy-frontend.yml`).

After creation, go to the resource → **Manage deployment token** → copy it.
That's your `AZURE_STATIC_WEB_APPS_API_TOKEN` secret.

The Static Web Apps URL will look like:
`https://happy-dune-01234.azurestaticapps.net`

---

## Step 4 — Set GitHub secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|--------|-------|
| `AZURE_CLIENT_ID` | from Step 2 JSON |
| `AZURE_TENANT_ID` | from Step 2 JSON |
| `AZURE_SUBSCRIPTION_ID` | from Step 2 JSON |
| `AZURE_RESOURCE_GROUP` | `greenroom-rg` |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | from Step 3 |
| `VITE_SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase → Project Settings → API → anon/public key |
| `VITE_API_URL` | `https://<your-api>.azurecontainerapps.io/api` |
| `SUPABASE_URL` | same as VITE_SUPABASE_URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → service_role key |
| `GROQ_API_KEY` | https://console.groq.com/keys |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `FALLBACK_BASE_URL` | `https://api.ollama.ai/v1` |
| `FALLBACK_API_KEY` | your Ollama cloud key |
| `FALLBACK_MODEL` | `llama3.3:70b` |
| `ALLOWED_ORIGINS` | `https://<your-app>.azurestaticapps.net` |

---

## Step 5 — Push and deploy

```bash
git push origin main
```

GitHub Actions runs two workflows, in sequence, not in parallel:
1. **CI** (`ci.yml`) — lint + test, both backend and frontend
2. **Build, Push & Deploy** (`deploy-containers.yml`) — only starts once CI reports success on `main` (via a `workflow_run` trigger, not an independent push trigger); builds both Docker images, pushes to `ghcr.io`, updates both Container Apps (backend and frontend — the frontend is a Container App too, not Azure Static Web Apps; Steps 1–4 above describe an earlier, no-longer-current topology), and polls `/api/health` afterward to confirm the new revision actually came up before calling the deploy done.

Watch progress at: https://github.com/VishwajeetRaut/greenroom/actions

---

## ⚠️ Piston privileged mode

Piston's code sandbox (`isolate`) requires `--privileged` Docker mode. Azure Container Apps
**free consumption plan does not support privileged containers**.

**What this means:** The API, auth, chat, and system-design tracks all work. The "Run Code"
and "Run Tests" buttons may return a sandbox error.

**Quick fix if code execution fails** — switch to Judge0 cloud (free tier, no setup):

1. Sign up at https://rapidapi.com/judge0-official/api/judge0-ce and get an API key.
2. Edit `backend/services/piston.py` — replace the `run_code` implementation with Judge0 calls.
   It's a one-file swap; the `RunCodeRequest` model and all callers stay the same.

For a full free deployment with working code execution, use a **Dedicated workload profile**
on Azure Container Apps (D4 plan) which supports privileged mode — but that costs ~$50/month.

---

## Observability — metrics, logs, live tail

### Local dev (Docker Compose)

`docker-compose.yml` (repo root) brings up the backend alongside Prometheus, Grafana, Loki, and Promtail:

```bash
cp backend/.env.example backend/.env   # fill in real keys first — required, compose will fail to start without this file
docker compose up -d --build
```

- **Grafana**: http://localhost:3000 (login `admin` / `admin`, set via `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml` — change this before exposing the stack beyond your own machine) → dashboard **"Greenroom Backend"** is auto-provisioned with request rate, p95 latency, error rate, and two live-tailing log panels (all logs, and errors only).
- **Prometheus**: http://localhost:9090 — scrapes `backend:8000/metrics` every 15s (config: `infra/prometheus/prometheus.yml`).
- **Loki**: receives logs via Promtail, which discovers containers through the Docker API (`infra/promtail/promtail-config.yml`) and ships their stdout — no extra instrumentation needed per-service.
- To watch raw logs in a terminal instead: `docker compose logs -f backend`.

This stack is **local-only** — it does not run against the live Azure deployment, and nothing here needs to be deployed for the app itself to work. It's for developers debugging locally.

### Live deployed app

The backend already logs one structured JSON line per event/request to stdout (`backend/services/logger.py`, `backend/main.py`) — every line, including per-request `http.request`/`http.request_failed` lines, now carries a `user_id` field (best-effort JWT `sub`, never used for authorization) — and exposes `GET /metrics` in Prometheus format. No extra setup needed to view raw logs on Azure:

```bash
az containerapp logs show --name greenroom-api --resource-group <your-rg> --follow
```

Or in the portal: **Container Apps → greenroom-api → Monitoring → Log stream**.

**For the same live-log-in-Grafana view the local compose stack gives you** (including filtering to one candidate's session), the Loki/Promtail stack above does **not** work against the live deployment — Azure Container Apps has no Docker socket for Promtail to read, so it only ever sees local traffic. The real path:

1. Deploy `infra/monitoring.bicep` (`infra/deploy-monitoring.sh --apply`) — this attaches (or reuses) a Log Analytics workspace, which Azure automatically starts forwarding Container Apps console logs into as `ContainerAppConsoleLogs_CL`.
2. Provision the Azure Monitor Logs Grafana data source: copy `infra/grafana/provisioning/datasources/azure-monitor.yml.example` to `azure-monitor.yml`, fill in the subscription/tenant/app-registration/workspace values, restart Grafana.
3. The "Live backend logs (production)" panel in the **Greenroom Backend** dashboard reads from that data source with a KQL query already wired to the dashboard's `$user_id` variable — paste a candidate's Supabase user id there to see just their session.

---

## Estimated monthly cost

| Service | Plan | Cost |
|---------|------|------|
| Azure Static Web Apps | Free | $0 |
| Azure Container Apps | Consumption (free grant: 180K vCPU-s/month) | $0* |
| Supabase | Free | $0 |
| Groq API | Free tier | $0 |
| **Total** | | **$0** |

*Free grant covers ~90 hours of active compute per month. Light traffic stays free.
