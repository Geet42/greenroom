import http from "k6/http";
import { sleep, check } from "k6";

const BASE = "https://greenroom-api.graybay-9c347e62.swedencentral.azurecontainerapps.io";

// 50 dedicated throwaway accounts (stress-test-1..50@greenroom.dev), one per
// VU — avoids the old script's problem of 5 VUs sharing one token, which
// tripped per-user rate-limiting/session-limit artifacts unrelated to real
// capacity.
//
// Tokens are pre-fetched into tokens.json by fetch_stress_tokens.py rather
// than logged in live from setup() — Supabase's own auth endpoint has an
// abuse-prevention rate limit on grant_type=password that a 50-account login
// burst tripped repeatedly across iterations of running this script. That
// script paces logins with backoff once; k6 just reads the result. Supabase
// access tokens last ~1h — if this file is stale, re-run
// fetch_stress_tokens.py first.
const tokens = JSON.parse(open("./tokens.json"));

export const options = {
  stages: [
    { duration: "20s", target: 5  },   // warm up
    { duration: "30s", target: 20 },   // ramp to 20 concurrent users
    { duration: "20s", target: 50 },   // spike to 50
    { duration: "20s", target: 0  },   // ramp down
  ],
  thresholds: {
    http_req_failed:   ["rate<0.10"],   // less than 10% failures
    http_req_duration: ["p(95)<8000"],  // 95% under 8s
  },
};

export default function () {
  const token = tokens[__VU % tokens.length];
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // 1. Start a behavioral session
  const start = http.post(
    `${BASE}/api/interview/start`,
    JSON.stringify({ track: "behavioral" }),
    { headers, tags: { name: "start" } }
  );
  check(start, {
    "start: 200":            (r) => r.status === 200,
    "start: not 429":        (r) => r.status !== 429,
    "start: not 500":        (r) => r.status !== 500,
    "start: has session_id": (r) => Boolean(r.json("session_id")),
  });

  if (start.status !== 200) return;
  const sessionId = start.json("session_id");

  sleep(1);

  // 2. Send a message (hits Groq — most likely failure point under load)
  const msg = http.post(
    `${BASE}/api/interview/message`,
    JSON.stringify({
      session_id: sessionId,
      message: "I have three years of backend engineering experience, mostly with Python and distributed systems.",
    }),
    { headers, tags: { name: "message" } }
  );
  check(msg, {
    "message: 200":        (r) => r.status === 200,
    "message: not 500":    (r) => r.status !== 500,
    "message: has question": (r) => Boolean(r.json("question")),
  });

  sleep(2);

  // 3. End session (hits Groq for evaluation — second likely failure point)
  const end = http.post(
    `${BASE}/api/interview/end`,
    JSON.stringify({ session_id: sessionId }),
    { headers, tags: { name: "end" } }
  );
  check(end, {
    "end: 200":       (r) => r.status === 200,
    "end: not 500":   (r) => r.status !== 500,
    "end: has score": (r) => r.json("overall_score") != null,
  });
}
