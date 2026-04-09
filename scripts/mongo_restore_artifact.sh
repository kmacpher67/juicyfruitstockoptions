#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=""
DROP_FLAG="--drop"

usage() {
  cat <<USAGE
Usage:
  $0 --artifact <artifact_dir> [--no-drop]
  $0 --latest [--no-drop]

Options:
  --artifact <dir>  Restore from a specific artifact directory.
  --latest          Restore from the latest artifact under ./backups/mongo.
  --no-drop         Do not pass --drop to mongorestore.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact)
      ARTIFACT_DIR="${2:-}"
      shift 2
      ;;
    --latest)
      ARTIFACT_DIR="__LATEST__"
      shift
      ;;
    --no-drop)
      DROP_FLAG=""
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$ARTIFACT_DIR" ]]; then
  usage
  exit 1
fi

if [[ "$ARTIFACT_DIR" == "__LATEST__" ]]; then
  CANDIDATES=""
  if [[ -d ./backups/mongo ]]; then
    CANDIDATES+="$(find ./backups/mongo -type f -name manifest.json -printf '%h\n' 2>/dev/null || true)\n"
  fi
  if [[ -d ./backups ]]; then
    CANDIDATES+="$(find ./backups -type f -name manifest.json -printf '%h\n' 2>/dev/null || true)\n"
  fi
  ARTIFACT_DIR="$(printf "%b" "$CANDIDATES" | awk 'NF' | sort -u | tail -n1)"
  if [[ -z "$ARTIFACT_DIR" ]]; then
    echo "ERROR: no artifacts found under ./backups or ./backups/mongo" >&2
    exit 1
  fi
fi

./scripts/mongo_backup_validate.sh "$ARTIFACT_DIR"

if [[ ! -d "$ARTIFACT_DIR/mongo_dump" ]]; then
  echo "ERROR: missing dump directory: $ARTIFACT_DIR/mongo_dump" >&2
  exit 1
fi

echo "Restoring from artifact: $ARTIFACT_DIR"
if [[ -n "$DROP_FLAG" ]]; then
  echo "Using --drop mode"
else
  echo "Using no-drop mode"
fi

if [[ -n "$DROP_FLAG" ]]; then
  ./scripts/restore_mongo.sh --drop "$ARTIFACT_DIR/mongo_dump"
else
  ./scripts/restore_mongo.sh "$ARTIFACT_DIR/mongo_dump"
fi

echo "Post-restore baseline counts:"
docker exec stock_portal_mongo mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval '
const d=db.getSiblingDB("stock_analysis");
const out={};
["users","user_settings","system_config","ibkr_holdings","ibkr_nav_history","ibkr_trades","stock_data"].forEach(c=>{out[c]=d.getCollection(c).countDocuments({});});
printjson(out);
'

echo "Restore complete."
