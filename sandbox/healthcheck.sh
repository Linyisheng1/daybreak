#!/bin/sh
set -eu

curl -fsS \
    -H "X-Sandbox-Token: ${SANDBOX_CONTROL_PROXY_TOKEN:?}" \
    http://127.0.0.1:8000/healthz >/dev/null
curl -fsS http://127.0.0.1:9222/json/version >/dev/null
nc -z 127.0.0.1 8080
