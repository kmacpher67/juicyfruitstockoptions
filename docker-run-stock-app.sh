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
#
# Optional JSON auto-restore on startup (safe defaults):
#   AUTO_RESTORE_JSON_ON_START=true ./docker-run-stock-app.sh
#   AUTO_RESTORE_JSON_ON_START=true AUTO_RESTORE_ONLY_IF_EMPTY=false ./docker-run-stock-app.sh
#   AUTO_RESTORE_JSON_ON_START=true AUTO_RESTORE_COLLECTION=stock_data ./docker-run-stock-app.sh

pip install -r requirements.txt
docker-compose up --build -d

sleep 5

if [[ "${AUTO_RESTORE_JSON_ON_START:-false}" == "true" ]]; then
  BACKUP_FILE="${AUTO_RESTORE_BACKUP_FILE:-mongo_backup.json}"
  TARGET_COLLECTION="${AUTO_RESTORE_COLLECTION:-stock_data}"
  ONLY_IF_EMPTY="${AUTO_RESTORE_ONLY_IF_EMPTY:-true}"
  MONGO_URI_LOCAL="${MONGO_URI_LOCAL:-mongodb://admin:admin123@localhost:27017/?authSource=admin}"

  if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "JSON auto-restore skipped: backup file not found: $BACKUP_FILE"
  else
    SHOULD_RESTORE="true"
    if [[ "$ONLY_IF_EMPTY" == "true" ]]; then
      COUNT=$(python3 -c "from pymongo import MongoClient; c=MongoClient('$MONGO_URI_LOCAL', serverSelectionTimeoutMS=5000); print(c['stock_analysis']['$TARGET_COLLECTION'].count_documents({}))")
      if [[ "$COUNT" != "0" ]]; then
        SHOULD_RESTORE="false"
        echo "JSON auto-restore skipped: stock_analysis.$TARGET_COLLECTION already has $COUNT document(s)."
      fi
    fi

    if [[ "$SHOULD_RESTORE" == "true" ]]; then
      echo "JSON auto-restore: importing $BACKUP_FILE into stock_analysis.$TARGET_COLLECTION"
      MONGO_COLLECTION_NAME="$TARGET_COLLECTION" ./scripts/reload_docker_mongo.sh "$BACKUP_FILE"
    fi
  fi
else
  echo "Tip: restore JSON backup manually with:"
  echo "  MONGO_COLLECTION_NAME=stock_data ./scripts/reload_docker_mongo.sh mongo_backup.json"
fi

# Run docker container ls to show operator that the container is running detached 
docker container ls
