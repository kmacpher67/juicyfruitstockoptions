#!/usr/bin/env bash
set -euo pipefail

# Build and start the FastAPI app with its MongoDB dependency.
# Extra arguments are passed through to docker-compose (e.g. -d for detached).
#
# Codex Version: After startup, you can reload a JSON backup into Docker Mongo with:
#   ./scripts/reload_docker_mongo.sh [mongo_backup.json]
#
# Claude Version: After startup, restore MongoDB data with one of:
#   Full DB restore (mongodump format):
#     ./scripts/restore_mongo.sh                  # restore from ./mongo_dump (default)
#     ./scripts/restore_mongo.sh /path/to/dump    # restore from specific mongodump directory
#     ./scripts/restore_mongo.sh --drop ./dump    # drop existing collections before restore
#
#   Legacy single-collection JSON restore:
#     ./scripts/reload_docker_mongo.sh [mongo_backup.json]
#
# To create a fresh mongodump backup of the running instance:
#   docker exec stock_portal_mongo mongodump \
#     --username admin --password admin123 --authenticationDatabase admin \
#     --out /tmp/mongo_dump && docker cp stock_portal_mongo:/tmp/mongo_dump ./mongo_dump

pip install -r requirements.txt
docker-compose up --build -d

sleep 5
# Run docker container ls to show operator that the container is running detached 
docker container ls
