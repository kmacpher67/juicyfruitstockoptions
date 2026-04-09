#!/usr/bin/env bash
set -euo pipefail

ARCHIVE_FILE="${1:-}"

if [[ -z "$ARCHIVE_FILE" ]]; then
  echo "Usage: $0 <archive_file.tar.gz>" >&2
  exit 1
fi

if [[ ! -f "$ARCHIVE_FILE" ]]; then
  echo "ERROR: archive file not found: $ARCHIVE_FILE" >&2
  exit 1
fi

mkdir -p ./backups

echo "Unpacking $ARCHIVE_FILE -> ./backups ..."
tar -xzf "$ARCHIVE_FILE" -C ./backups

LATEST_ARTIFACT="$(find ./backups -type f -name manifest.json -printf '%h\n' | sort | tail -n1)"
if [[ -z "$LATEST_ARTIFACT" ]]; then
  echo "WARN: unpack finished but no manifest.json found." >&2
  exit 1
fi

echo "Unpack complete. Detected artifact: $LATEST_ARTIFACT"
echo "Validate: ./scripts/mongo_backup_validate.sh '$LATEST_ARTIFACT'"
echo "Restore : ./scripts/mongo_restore_artifact.sh --artifact '$LATEST_ARTIFACT'"
