#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-mongo_backup.json}"
MONGO_URI="${MONGO_URI:-mongodb://admin:admin123@localhost:27017/?authSource=admin}"
MONGO_DB_NAME="${MONGO_DB_NAME:-stock_analysis}"
MONGO_COLLECTION_NAME="${MONGO_COLLECTION_NAME:-test_stock_data}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH."
  exit 1
fi

if ! docker container inspect stock_portal_mongo >/dev/null 2>&1; then
  echo "Error: stock_portal_mongo container was not found."
  echo "Start the stack first with ./docker-run-stock-app.sh or docker-compose up -d."
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' stock_portal_mongo 2>/dev/null)" != "true" ]; then
  echo "Error: stock_portal_mongo exists but is not running."
  echo "Start it first with ./docker-run-stock-app.sh or docker-compose up -d."
  exit 1
fi

echo "Reloading ${BACKUP_FILE} into ${MONGO_DB_NAME}.${MONGO_COLLECTION_NAME} via ${MONGO_URI}"
python3 restore_mongo.py \
  --input-file "${BACKUP_FILE}" \
  --mongo-uri "${MONGO_URI}" \
  --db-name "${MONGO_DB_NAME}" \
  --collection-name "${MONGO_COLLECTION_NAME}"
