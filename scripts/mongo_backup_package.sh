#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=""
OUT_FILE=""

usage() {
  cat <<USAGE
Usage:
  $0 --artifact <artifact_dir>
  $0 --latest

Options:
  --artifact <dir>  Package a specific artifact directory.
  --latest          Package latest artifact (searches ./backups/mongo then ./backups).
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
    echo "ERROR: no artifact found under ./backups or ./backups/mongo" >&2
    exit 1
  fi
fi

./scripts/mongo_backup_validate.sh "$ARTIFACT_DIR" >/dev/null

REL="$ARTIFACT_DIR"
REL="${REL#./backups/}"
REL="${REL#$PWD/backups/}"
if [[ "$REL" == "$ARTIFACT_DIR" ]]; then
  echo "ERROR: artifact must be under ./backups for stable packaging path" >&2
  exit 1
fi

BACKUP_ID="$(basename "$ARTIFACT_DIR")"
OUT_FILE="./backups/mongo_backup_${BACKUP_ID}.tar.gz"

echo "Packaging $ARTIFACT_DIR -> $OUT_FILE"
tar -czf "$OUT_FILE" -C ./backups "$REL"

echo "Package created: $OUT_FILE"
echo "On target host, unpack with:"
echo "  ./scripts/mongo_backup_unpack.sh '$OUT_FILE'"
