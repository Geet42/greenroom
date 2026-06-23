#!/bin/bash
# Runs on container start: installs language runtimes into /piston/packages,
# then re-execs the Piston API server in foreground.
set -euo pipefail

PACKAGES_DIR="/piston/packages"
LOCK_FILE="$PACKAGES_DIR/.installed"

if [ -f "$LOCK_FILE" ]; then
    echo "[piston-init] Runtimes already present — skipping install."
    exec node /piston_api/index.js
fi

echo "[piston-init] Starting Piston to install runtimes (one-time, ~3 min)..."
node /piston_api/index.js &
SERVER_PID=$!

# Wait until the REST API responds
for i in $(seq 1 60); do
    curl -sf http://localhost:2000/api/v2/runtimes > /dev/null 2>&1 && break
    sleep 3
done

install_runtime() {
    local lang=$1 ver=$2
    echo "[piston-init] Installing $lang $ver..."
    curl -sf -X POST http://localhost:2000/api/v2/packages \
        -H "Content-Type: application/json" \
        -d "{\"language\":\"$lang\",\"version\":\"$ver\"}" \
        | grep -o '"download":"[^"]*"' || true
}

install_runtime python 3.10.0
install_runtime node   18.15.0
install_runtime java   15.0.2
install_runtime gcc    10.2.0

touch "$LOCK_FILE"
echo "[piston-init] Done. Restarting Piston..."
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true

exec node /piston_api/index.js
