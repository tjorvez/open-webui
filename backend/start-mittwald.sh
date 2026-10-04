#!/usr/bin/env bash
set -euo pipefail

# mittwald runs the image filesystem read-only. Keep generated assets and
# library caches in the writable runtime volume; application data has its own volume.
export HOME="${HOME:-/tmp/open-webui/home}"
export STATIC_DIR="${STATIC_DIR:-/tmp/open-webui/static}"
mkdir -p "$HOME" "$STATIC_DIR"
cp -R /app/backend/open_webui/static/. "$STATIC_DIR/"
exec bash /app/backend/start.sh "$@"
