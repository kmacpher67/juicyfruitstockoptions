#!/usr/bin/env bash
set -euo pipefail

MONGO_CONTAINER="${MONGO_CONTAINER:-stock_portal_mongo}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASS="${MONGO_PASS:-admin123}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"
TARGET_DB="${TARGET_DB:-stock_analysis}"
BACKUP_ROOT="${BACKUP_ROOT:-./backups/mongo}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

if ! docker container inspect "$MONGO_CONTAINER" >/dev/null 2>&1; then
  echo "ERROR: Mongo container '$MONGO_CONTAINER' not found." >&2
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$MONGO_CONTAINER")" != "true" ]]; then
  echo "ERROR: Mongo container '$MONGO_CONTAINER' is not running." >&2
  exit 1
fi

DATE_PATH="$(date -u +%Y/%m/%d)"
TS_ID="$(date -u +%Y%m%dT%H%M%SZ)"
ARTIFACT_DIR="$BACKUP_ROOT/$DATE_PATH/$TS_ID"
DUMP_DIR="$ARTIFACT_DIR/mongo_dump"

mkdir -p "$ARTIFACT_DIR"

echo "[1/5] Creating mongodump in container..."
docker exec "$MONGO_CONTAINER" sh -lc "rm -rf /tmp/mongo_dump && mkdir -p /tmp/mongo_dump && mongodump --username '$MONGO_USER' --password '$MONGO_PASS' --authenticationDatabase '$MONGO_AUTH_DB' --out /tmp/mongo_dump"

echo "[2/5] Copying mongodump to $DUMP_DIR ..."
docker cp "$MONGO_CONTAINER":/tmp/mongo_dump "$DUMP_DIR"
docker exec "$MONGO_CONTAINER" rm -rf /tmp/mongo_dump

echo "[3/5] Collecting manifest metadata..."
CREATED_AT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SOURCE_HOST="$(hostname)"
SOURCE_OS="$(uname -srm)"
MONGO_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$MONGO_CONTAINER")"
MONGO_VERSION="$(docker exec "$MONGO_CONTAINER" mongod --version | awk '/db version/ {print $3; exit}')"
MONGODUMP_VERSION="$(docker exec "$MONGO_CONTAINER" mongodump --version | head -n1 | tr -d '\r')"
MONGORESTORE_VERSION="$(docker exec "$MONGO_CONTAINER" mongorestore --version | head -n1 | tr -d '\r')"

DATABASE_NAMES_JSON="$(docker exec "$MONGO_CONTAINER" mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" --eval 'JSON.stringify(db.adminCommand({listDatabases:1}).databases.map(d=>d.name).sort())')"

STOCK_SUMMARY_JSON="$(docker exec "$MONGO_CONTAINER" mongosh --quiet -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" --eval "const d=db.getSiblingDB('$TARGET_DB'); const names=d.getCollectionNames().sort(); const counts={}; names.forEach(c=>counts[c]=d.getCollection(c).countDocuments({})); print(JSON.stringify({db:'$TARGET_DB', collections:names, collection_counts:counts}));")"

cat > "$ARTIFACT_DIR/manifest.json" <<MANIFEST
{
  "backup_id": "$TS_ID",
  "created_at_utc": "$CREATED_AT_UTC",
  "source_host": "$SOURCE_HOST",
  "source_os": "$SOURCE_OS",
  "mongo_container": "$MONGO_CONTAINER",
  "mongo_image": "$MONGO_IMAGE",
  "mongo_version": "$MONGO_VERSION",
  "database_names": $DATABASE_NAMES_JSON,
  "stock_analysis_summary": $STOCK_SUMMARY_JSON,
  "tool_versions": {
    "mongodump": "$MONGODUMP_VERSION",
    "mongorestore": "$MONGORESTORE_VERSION"
  },
  "notes": "Full MongoDB dump artifact with checksum manifest"
}
MANIFEST


echo "[4/5] Generating checksums..."
(
  cd "$ARTIFACT_DIR"
  find . -type f ! -name 'sha256sums.txt' -print0 | sort -z | xargs -0 sha256sum > sha256sums.txt
)

echo "[5/5] Done"
echo "Artifact: $ARTIFACT_DIR"
echo "Run validation: ./scripts/mongo_backup_validate.sh '$ARTIFACT_DIR'"
