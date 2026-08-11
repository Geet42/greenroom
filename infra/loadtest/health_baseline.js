// Baseline capacity/concurrency test against unauthenticated endpoints
// (/api/health, /metrics) — no Supabase token needed, so this can run
// anywhere without creating test accounts or touching real session data.
// Pair with the docker-compose Grafana dashboard (localhost:3000) to watch
// request rate/latency/errors live while this runs.
//
// Usage:
//   docker run --rm -i --network host \
//     -e BASE_URL=http://localhost:8000 \
//     grafana/k6 run - < infra/loadtest/health_baseline.js
//
// (On Docker Desktop for Windows/Mac, --network host doesn't work — use
//  -e BASE_URL=http://host.docker.internal:8000 instead, no --network flag.)
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const errorRate = new Rate("errors");
export const healthLatency = new Trend("health_latency_ms", true);

export const options = {
  scenarios: {
    ramping: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 20 },   // ramp to 20 concurrent
        { duration: "1m", target: 50 },    // ramp to 50 concurrent
        { duration: "1m", target: 50 },    // hold at 50
        { duration: "30s", target: 0 },    // ramp down
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],       // <1% errors
    http_req_duration: ["p(95)<500"],     // p95 under 500ms
    errors: ["rate<0.01"],
  },
};

// /api/health makes a LIVE external call to Judge0's public API on every
// single hit (main.py — no caching), which has no SLA and isn't ours to
// hammer. /metrics is pure in-process Prometheus state, so it's the right
// target for a repeated-load baseline; /api/health is only sampled
// occasionally (every ~20th iteration) to still prove it works under
// concurrent load without turning this into an unsolicited load test of a
// third party's free service.
export default function () {
  const metricsRes = http.get(`${BASE_URL}/metrics`);
  const ok = check(metricsRes, { "metrics status is 200": (r) => r.status === 200 });
  errorRate.add(!ok);

  if (__ITER % 20 === 0) {
    const res = http.get(`${BASE_URL}/api/health`);
    healthLatency.add(res.timings.duration);
    check(res, {
      "health: status is 200": (r) => r.status === 200,
      "health: body has status field": (r) => {
        try {
          return JSON.parse(r.body).status !== undefined;
        } catch {
          return false;
        }
      },
    });
  }

  sleep(0.5);
}
