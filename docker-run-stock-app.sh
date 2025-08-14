#!/usr/bin/env bash
set -euo pipefail

# Build and start the FastAPI app with its MongoDB dependency.
# Extra arguments are passed through to docker-compose (e.g. -d for detached).

docker-compose up --build "$@"

