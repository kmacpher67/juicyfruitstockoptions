#!/usr/bin/env bash
set -euo pipefail

# Build and start the FastAPI app with its MongoDB dependency.
# Extra arguments are passed through to docker-compose (e.g. -d for detached).

pip install -r requirements.txt
docker-compose up --build -d

sleep 5
# Run docker container ls to show operator that the container is running detached 
docker container ls