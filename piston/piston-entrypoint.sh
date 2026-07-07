#!/bin/bash
# Interim sandbox hardening — best-effort resource caps for the Piston process.
#
# Azure Container Apps does not grant --privileged mode, so Piston cannot use
# its built-in isolate sandbox (which requires CAP_SYS_ADMIN). Until we migrate
# to gVisor/nsjail (item 8 in the remediation plan), we apply ulimits at the
# shell level to limit damage from runaway or malicious code submissions.
#
# These limits apply to this shell and all child processes (including the Node
# process that runs Piston and the language runtimes it spawns).
#
# ⚠️  BEST-EFFORT LABEL: ulimits are not a security boundary — they reduce
# blast radius but do not prevent a determined attacker from escaping them.
# Do NOT advertise this as full sandboxing in any external-facing material.

set -euo pipefail

# CPU time per process: 10 seconds hard limit
# Prevents infinite-loop submissions from burning CPU indefinitely.
ulimit -t 10

# Max file size created by any child process: 16 MB
# Prevents fork-bomb variants that write giant files to fill the container disk.
ulimit -f 16384

# Max number of open file descriptors: 64
# Reduces surface for FD-exhaustion attacks.
ulimit -n 64

# Max number of processes per UID: 64
# Makes classic fork-bomb patterns hit a wall quickly.
# Note: this caps processes for the UID running this script — Piston runs as
# root inside the container (upstream image), so this limit applies to root.
ulimit -u 64

# Max resident set size: 256 MB (in KB)
# Caps memory per process to prevent OOM-kills taking down the whole container.
ulimit -m 262144
ulimit -v 262144

echo "[piston-entrypoint] Resource caps applied (best-effort, not a full sandbox)."
exec /usr/local/bin/install-packages.sh
