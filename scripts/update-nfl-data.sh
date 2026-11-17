#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
fail() { printf '%s\n' "$1" >&2; exit 3; }
command -v docker >/dev/null || fail 'Docker is missing. Install/configure Docker Desktop WSL integration first.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose is unavailable.'
docker compose --profile scheduler config --quiet 2>/dev/null || fail 'Compose configuration is invalid. Check the existing private .env; do not print credentials.'
docker info >/dev/null 2>&1 || fail 'Docker daemon is unavailable or its socket is inaccessible.'
for service in db api; do
  container=$(docker compose ps -q "$service" 2>/dev/null) || fail "Cannot inspect required service $service."
  [[ -n "$container" ]] || fail "Required service $service is not running. Start the existing db/api services first."
  health=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null) || fail "Cannot inspect health for $service."
  [[ "$health" == healthy ]] || fail "Required service $service is not healthy. Inspect its health before updating."
done
if [[ "${1:-}" != --status ]]; then
  daemon=$(docker compose --profile scheduler ps --status running -q scheduler 2>/dev/null) || fail 'Cannot inspect scheduler coordination state.'
  [[ -z "$daemon" ]] || fail 'Recurring scheduler is running. Coordinate its shutdown with docker compose --profile scheduler stop scheduler, then retry. No locks were removed.'
  [[ -t 0 && -t 1 ]] || fail 'Interactive terminal required. Use --status for read-only noninteractive inspection.'
  exec docker compose --profile scheduler run --rm --no-deps scheduler python -m ingestion.update_cli "$@"
fi
exec docker compose --profile scheduler run -T --rm --no-deps scheduler python -m ingestion.update_cli "$@"
