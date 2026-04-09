#!/usr/bin/env bash
set -euo pipefail

# Build and start the FastAPI app with its MongoDB dependency.
# Extra arguments are passed through to docker-compose (e.g. -d for detached).
#
# Preferred restore path (default): full DB restore using mongodump artifacts.
#   ./scripts/restore_mongo.sh                  # restore from ./mongo_dump (default)
#   ./scripts/restore_mongo.sh /path/to/dump    # restore from specific mongodump directory
#   ./scripts/restore_mongo.sh --drop ./dump    # drop existing collections before restore
#
# Legacy fallback path: single-collection JSON restore (stock_data only).
#   ./scripts/reload_docker_mongo.sh [mongo_backup.json]
#
# To create a fresh mongodump backup of the running instance:
#   docker exec stock_portal_mongo mongodump \
#     --username admin --password admin123 --authenticationDatabase admin \
#     --out /tmp/mongo_dump && docker cp stock_portal_mongo:/tmp/mongo_dump ./mongo_dump
#
# Optional auto-restore controls (defaults prioritize full DB restore):
#   AUTO_RESTORE_ON_START=false ./docker-run-stock-app.sh
#   AUTO_RESTORE_MODE=dump ./docker-run-stock-app.sh   # force mongodump restore mode
#   AUTO_RESTORE_MODE=json ./docker-run-stock-app.sh   # force legacy JSON restore mode
#   AUTO_RESTORE_ONLY_IF_EMPTY=false ./docker-run-stock-app.sh

# pip install -r requirements.txt
docker compose up --build -d

sleep 3

AUTO_RESTORE_ON_START="${AUTO_RESTORE_ON_START:-true}"
AUTO_RESTORE_MODE="${AUTO_RESTORE_MODE:-auto}"  # auto|dump|json
ONLY_IF_EMPTY="${AUTO_RESTORE_ONLY_IF_EMPTY:-true}"
MONGO_URI_LOCAL="${MONGO_URI_LOCAL:-mongodb://admin:admin123@localhost:27017/?authSource=admin}"
DUMP_DIR="${AUTO_RESTORE_DUMP_DIR:-./mongo_dump}"
BACKUP_FILE="${AUTO_RESTORE_BACKUP_FILE:-mongo_backup.json}"
TARGET_COLLECTION="${AUTO_RESTORE_COLLECTION:-stock_data}"

if [[ "$AUTO_RESTORE_ON_START" == "true" ]]; then
  echo "Waiting for Mongo readiness..."
  for i in {1..30}; do
    if docker exec stock_portal_mongo mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval "db.runCommand({ ping: 1 }).ok" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  DB_DOC_COUNT=$(python3 -c "from pymongo import MongoClient; c=MongoClient('$MONGO_URI_LOCAL', serverSelectionTimeoutMS=5000); db=c['stock_analysis']; print(sum(db[name].estimated_document_count() for name in db.list_collection_names()))" 2>/dev/null || echo "unknown")
  SHOULD_RESTORE="true"
  if [[ "$ONLY_IF_EMPTY" == "true" && "$DB_DOC_COUNT" != "0" && "$DB_DOC_COUNT" != "unknown" ]]; then
    SHOULD_RESTORE="false"
    echo "Auto-restore skipped: stock_analysis already has ${DB_DOC_COUNT} document(s)."
  fi

  if [[ "$SHOULD_RESTORE" == "true" ]]; then
    if [[ "$AUTO_RESTORE_MODE" == "dump" || ( "$AUTO_RESTORE_MODE" == "auto" && -d "$DUMP_DIR" ) ]]; then
      if [[ -d "$DUMP_DIR" ]]; then
        echo "Auto-restore: restoring full Mongo dump from $DUMP_DIR"
        ./scripts/restore_mongo.sh "$DUMP_DIR"
      else
        echo "Auto-restore dump mode requested, but dump directory not found: $DUMP_DIR"
      fi
    elif [[ "$AUTO_RESTORE_MODE" == "json" || ( "$AUTO_RESTORE_MODE" == "auto" && -f "$BACKUP_FILE" ) ]]; then
      if [[ -f "$BACKUP_FILE" ]]; then
        echo "Auto-restore: importing legacy JSON backup into stock_analysis.$TARGET_COLLECTION from $BACKUP_FILE"
        MONGO_COLLECTION_NAME="$TARGET_COLLECTION" ./scripts/reload_docker_mongo.sh "$BACKUP_FILE"
      else
        echo "Auto-restore JSON mode requested, but backup file not found: $BACKUP_FILE"
      fi
    else
      echo "Auto-restore skipped: no compatible backup source found (looked for $DUMP_DIR or $BACKUP_FILE)."
    fi
  fi
else
  echo "Auto-restore disabled via AUTO_RESTORE_ON_START=false"
  echo "Manual full restore (recommended): ./scripts/restore_mongo.sh ./mongo_dump"
  echo "Manual legacy JSON restore: MONGO_COLLECTION_NAME=stock_data ./scripts/reload_docker_mongo.sh mongo_backup.json"
fi

# Run docker container ls to show operator that the container is running detached 
docker container ls
