#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

case "${1:-up}" in
  up)
    docker compose up -d --build --wait
    ;;
  down)
    docker compose down
    ;;
  test)
    uv run pytest -v
    ;;
  ingest-sample)
    make ingest-sample
    ;;
  *)
    echo "Usage: $0 {up|down|test|ingest-sample}"
    exit 1
    ;;
esac
