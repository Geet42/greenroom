// Load test for the actual interview flow (start -> message -> end) — the
// expensive path (Groq/Azure/Judge0 calls), unlike health_baseline.js. This
// requires a REAL Supabase auth token(s), since every route here is behind
// get_current_user — there is no safe way to fabricate that from a script.
//
// Concurrency is capped by design, not by k6 config: MAX_ACTIVE_SESSIONS=3
// and the 30 req/min rate limiter (services/session_guard.py,
// services/rate_limit.py) apply PER USER, so hammering this with many VUs
// sharing one token mostly just measures the rate limiter rejecting you,
// not real backend capacity. Pass AUTH_TOKENS (comma-separated) with one
// token per distinct test user to get genuine concurrency; with a single
// AUTH_TOKEN this intentionally stays small (see options.vus below).
//
// Getting a token: log into the app in a browser, open devtools ->
// Application -> Local Storage -> find the Supabase session, copy
// access_token. Tokens expire (usually 1h) — grab a fresh one if this
// starts 401ing partway through a run.
//
// Usage:
//   docker run --rm -i \
//     -e BASE_URL=http://host.docker.internal:8000 \
//     -e AUTH_TOKENS=eyJ...,eyJ...  \
//     grafana/k6 run - < infra/loadtest/interview_flow.js
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TOKENS = (__ENV.AUTH_TOKENS || __ENV.AUTH_TOKEN || "").split(",").map((t) => t.trim()).filter(Boolean);

if (TOKENS.length === 0) {
  throw new Error("Set AUTH_TOKENS (or AUTH_TOKEN) to a real Supabase access_token — see file header.");
}

export const startLatency = new Trend("interview_start_latency_ms", true);
export const messageLatency = new Trend("interview_message_latency_ms", true);
export const endLatency = new Trend("interview_end_latency_ms", true);

export const options = {
  // Deliberately small and duration-capped — see file header. Bump `vus`
  // toward TOKENS.length if you supplied multiple distinct users.
  vus: Math.min(3, TOKENS.length),
  duration: "3m",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    interview_start_latency_ms: ["p(95)<15000"],   // LLM call — generous budget
    interview_message_latency_ms: ["p(95)<15000"],
    interview_end_latency_ms: ["p(95)<30000"],       // evaluation is 1-2 LLM calls
  },
};

function authHeaders(token) {
  return { headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } };
}

export default function () {
  const token = TOKENS[__VU % TOKENS.length];
  const headers = authHeaders(token);

  const startRes = http.post(
    `${BASE_URL}/api/interview/start`,
    JSON.stringify({ track: "behavioral", role: "Software Engineer" }),
    headers,
  );
  startLatency.add(startRes.timings.duration);
  const startOk = check(startRes, { "start: 200": (r) => r.status === 200 });
  if (!startOk) {
    console.error(`start failed: ${startRes.status} ${startRes.body}`);
    sleep(2);
    return;
  }
  const sessionId = JSON.parse(startRes.body).session_id;

  sleep(1);

  const messageRes = http.post(
    `${BASE_URL}/api/interview/message`,
    JSON.stringify({
      session_id: sessionId,
      message: "In my last role I led the migration of our monolith to microservices, which reduced deploy time by 40%.",
    }),
    headers,
  );
  messageLatency.add(messageRes.timings.duration);
  check(messageRes, { "message: 200": (r) => r.status === 200 });

  sleep(1);

  const endRes = http.post(
    `${BASE_URL}/api/interview/end`,
    JSON.stringify({ session_id: sessionId }),
    headers,
  );
  endLatency.add(endRes.timings.duration);
  check(endRes, { "end: 200": (r) => r.status === 200 });

  sleep(2);
}
