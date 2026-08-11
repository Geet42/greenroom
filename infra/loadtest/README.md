# Load testing

Two k6 scripts, run via the official `grafana/k6` Docker image (no local k6
install needed):

- **`health_baseline.js`** — unauthenticated (`/api/health`, `/metrics`),
  ramps to 50 concurrent virtual users. Safe to run anytime, creates no
  data. Measures raw server capacity/concurrency handling, independent of
  the LLM-calling paths.
- **`interview_flow.js`** — the real, expensive path (session start →
  message → end, hitting Groq/Azure/Judge0). Requires a real Supabase
  access token (see the file header) and is deliberately small/short —
  `MAX_ACTIVE_SESSIONS` and the per-user rate limiter cap what a single
  token can do, by design (see services/session_guard.py).

## Running

```bash
# Bring the backend up (see docker-compose.yml at repo root)
docker compose up -d backend

# Baseline (no auth needed)
docker run --rm -i \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run - < infra/loadtest/health_baseline.js

# Interview flow (needs a real token — grab one from the browser: log in,
# devtools -> Application -> Local Storage -> Supabase session -> access_token)
docker run --rm -i \
  -e BASE_URL=http://host.docker.internal:8000 \
  -e AUTH_TOKEN=eyJ... \
  grafana/k6 run - < infra/loadtest/interview_flow.js
```

Watch the results live in the Grafana dashboard (`localhost:3000`, see repo
root `docker-compose.yml`) alongside k6's own end-of-run summary.

## Findings / mitigations

See `infra/loadtest/FINDINGS.md` for results from the last run against this
environment and what (if anything) they justify changing. Don't add
mitigations here speculatively — only after a real run surfaces an actual
bottleneck.
