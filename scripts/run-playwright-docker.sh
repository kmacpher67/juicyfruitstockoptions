#!/usr/bin/env bash

set -euo pipefail

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.e2e.yml)

cleanup() {
  docker compose "${COMPOSE_FILES[@]}" down --remove-orphans
}

trap cleanup EXIT

docker compose "${COMPOSE_FILES[@]}" up --build --abort-on-container-exit --exit-code-from playwright playwright
