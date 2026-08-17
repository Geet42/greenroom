"""Fetches fresh access tokens for the 50 stress-test-N@greenroom.dev
accounts and writes them to tokens.json, which stress.js reads at test start.

Paces logins with backoff on 429 — Supabase's own auth endpoint has an
abuse-prevention rate limit on grant_type=password, independent of this app's
own rate limiter, that a tight 50-account login burst trips easily.

Run this whenever tokens.json is missing or its tokens have expired
(Supabase access tokens last ~1h):

    python3 stress/fetch_stress_tokens.py
"""
import json
import time
import urllib.error
import urllib.request

SUPABASE_URL = "https://lxtvixfitdgmnrugooqf.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx4dHZpeGZpdGRnbW5ydWdvb3FmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE1NTIwNzcsImV4cCI6MjA5NzEyODA3N30.XLazKscB5b3rTbTBqjCYbd6N4ZCwf1o5DLQQGAWwQpc"
PASSWORD = "StressTest-Greenroom-2026!"
NUM_ACCOUNTS = 50
OUT_PATH = "tokens.json"


def main() -> None:
    tokens = []
    delay = 3.0
    for i in range(1, NUM_ACCOUNTS + 1):
        email = f"stress-test-{i}@greenroom.dev"
        while True:
            req = urllib.request.Request(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                data=json.dumps({"email": email, "password": PASSWORD}).encode(),
                headers={"Content-Type": "application/json", "apikey": ANON_KEY},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode())
                tokens.append(data["access_token"])
                print(f"{i}/{NUM_ACCOUNTS} ok")
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"{i}/{NUM_ACCOUNTS} rate-limited, backing off {delay}s")
                    time.sleep(delay)
                    delay = min(delay * 1.5, 20)
                    continue
                raise
        time.sleep(1.0)

    with open(OUT_PATH, "w") as f:
        json.dump(tokens, f)
    print(f"wrote {len(tokens)} tokens to {OUT_PATH}")


if __name__ == "__main__":
    main()
