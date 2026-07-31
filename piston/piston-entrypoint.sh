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

# Max number of open file descriptors: 512
# Node.js needs ~100+ FDs just at startup (libuv, module loader, timers);
# 64 caused EMFILE errors and crun clone failures under normal Piston load.
ulimit -n 512

# Max number of processes per UID: 256
# Piston (Node.js) + each code run spawns several child processes. 64 was
# too tight — crun clone() returned EAGAIN before the submitted code could
# even start, producing "OCI runtime error: crun: clone: Resource temporarily
# unavailable". 256 still kills a fork-bomb quickly while giving Piston
# enough room to operate.
ulimit -u 256

# Memory is intentionally NOT capped here with ulimit -m / -v.
# V8 reserves a large virtual address range for its JIT code cache at startup
# even when physical RSS stays low; a 256 MB virtual-memory ulimit causes
# "Fatal process OOM in CodeRange setup" before Node.js is usable. The
# container's 1 Gi cgroup memory limit is already enforced by the host kernel
# and is the correct mechanism for bounding Piston's footprint.

echo "[piston-entrypoint] Resource caps applied (best-effort, not a full sandbox)."
exec /usr/local/bin/install-packages.sh
