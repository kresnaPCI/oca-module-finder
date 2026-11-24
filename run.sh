#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p "${VIDEO_DIR:-./videos}"
export CAST_PORT="${CAST_PORT:-8765}"

echo "Cast Hub → http://$(ipconfig getifaddr en0 2>/dev/null || hostname):${CAST_PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${CAST_PORT}"
