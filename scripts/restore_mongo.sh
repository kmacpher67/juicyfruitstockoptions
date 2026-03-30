#!/usr/bin/env bash
# restore_mongo.sh — Restore a mongodump backup into the running Docker MongoDB instance.
#
# Usage:
#   ./scripts/restore_mongo.sh                        # restores from ./mongo_dump (default)
#   ./scripts/restore_mongo.sh /path/to/dump_dir      # restores from a specific dump directory
#   ./scripts/restore_mongo.sh --drop /path/to/dump   # drop collections before restoring
#
# The dump directory should be the output of: mongodump --out ./mongo_dump
# MongoDB container must be running (start with: ./docker-run-stock-app.sh)

set -euo pipefail

MONGO_CONTAINER="stock_portal_mongo"
MONGO_USER="admin"
MONGO_PASS="admin123"
MONGO_AUTH_DB="admin"
DROP_FLAG=""
DUMP_DIR="./mongo_dump"

# Parse arguments
for arg in "$@"; do
  if [[ "$arg" == "--drop" ]]; then
    DROP_FLAG="--drop"
  elif [[ "$arg" != --* ]]; then
    DUMP_DIR="$arg"
  fi
done

# Verify dump directory exists
if [[ ! -d "$DUMP_DIR" ]]; then
  echo "ERROR: Dump directory not found: $DUMP_DIR"
  echo ""
  echo "To create a backup first, run:"
  echo "  docker exec $MONGO_CONTAINER mongodump \\"
  echo "    --username $MONGO_USER --password $MONGO_PASS --authenticationDatabase $MONGO_AUTH_DB \\"
  echo "    --out /tmp/mongo_dump"
  echo "  docker cp $MONGO_CONTAINER:/tmp/mongo_dump ./mongo_dump"
  exit 1
fi

# Verify MongoDB container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${MONGO_CONTAINER}$"; then
  echo "ERROR: MongoDB container '$MONGO_CONTAINER' is not running."
  echo "Start the stack first with: ./docker-run-stock-app.sh"
  exit 1
fi

DUMP_DIR_ABS=$(realpath "$DUMP_DIR")
echo "Restoring from: $DUMP_DIR_ABS"
if [[ -n "$DROP_FLAG" ]]; then
  echo "WARNING: --drop flag set — existing collections will be dropped before restore."
fi
echo ""

# Copy dump into the container
echo "[1/3] Copying dump into container..."
docker cp "$DUMP_DIR_ABS" "$MONGO_CONTAINER":/tmp/mongo_restore_dump

# Run mongorestore inside the container
echo "[2/3] Running mongorestore..."
docker exec "$MONGO_CONTAINER" mongorestore \
  --username "$MONGO_USER" \
  --password "$MONGO_PASS" \
  --authenticationDatabase "$MONGO_AUTH_DB" \
  $DROP_FLAG \
  /tmp/mongo_restore_dump

# Clean up temp files in container
echo "[3/3] Cleaning up temp files in container..."
docker exec "$MONGO_CONTAINER" rm -rf /tmp/mongo_restore_dump

echo ""
echo "Restore complete."
