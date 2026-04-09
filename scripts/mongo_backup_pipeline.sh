#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${WORKDIR:-$(pwd)}"
LOG_DIR="${LOG_DIR:-$WORKDIR/logs}"
mkdir -p "$LOG_DIR"

# Optional upload hook. If set, this command is called with one arg: <package_file>
# Example with rclone (once configured):
#   BACKUP_UPLOAD_CMD='rclone copyto' BACKUP_UPLOAD_TARGET='gdrive:JuicyFruit/mongo_backups'
BACKUP_UPLOAD_CMD="${BACKUP_UPLOAD_CMD:-}"
BACKUP_UPLOAD_TARGET="${BACKUP_UPLOAD_TARGET:-}"
DRIVE_FOLDER_ID="${DRIVE_FOLDER_ID:-}"
DRIVE_RETENTION_DAYS="${DRIVE_RETENTION_DAYS:-30}"
DRIVE_RETENTION_KEEP_MIN="${DRIVE_RETENTION_KEEP_MIN:-10}"

run_find_latest_artifact() {
  local candidates=""
  if [[ -d "$WORKDIR/backups/mongo" ]]; then
    candidates+="$(find "$WORKDIR/backups/mongo" -type f -name manifest.json -printf '%h\n' 2>/dev/null || true)\n"
  fi
  if [[ -d "$WORKDIR/backups" ]]; then
    candidates+="$(find "$WORKDIR/backups" -type f -name manifest.json -printf '%h\n' 2>/dev/null || true)\n"
  fi
  printf "%b" "$candidates" | awk 'NF' | sort -u | tail -n1
}

cd "$WORKDIR"

echo "[pipeline] starting mongo backup pipeline at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -n "$DRIVE_FOLDER_ID" ]]; then
  if [[ -z "${DRIVE_ACCESS_TOKEN:-}" && -z "${DRIVE_ACCESS_TOKEN_CMD:-}" ]]; then
    echo "[pipeline] ERROR: DRIVE_FOLDER_ID is set but no token source is configured." >&2
    echo "[pipeline] Set one of:" >&2
    echo "[pipeline]   DRIVE_ACCESS_TOKEN='<oauth_access_token>'" >&2
    echo "[pipeline]   DRIVE_ACCESS_TOKEN_CMD='gcloud auth application-default print-access-token'" >&2
    exit 1
  fi
fi

BEFORE_ARTIFACT="$(run_find_latest_artifact || true)"

./scripts/mongo_backup_artifact.sh

AFTER_ARTIFACT="$(run_find_latest_artifact || true)"
if [[ -z "$AFTER_ARTIFACT" ]]; then
  echo "[pipeline] ERROR: could not detect backup artifact after creation" >&2
  exit 1
fi

ARTIFACT_DIR="$AFTER_ARTIFACT"
if [[ -n "$BEFORE_ARTIFACT" && "$AFTER_ARTIFACT" == "$BEFORE_ARTIFACT" ]]; then
  echo "[pipeline] WARN: latest artifact unchanged; using $ARTIFACT_DIR"
fi

# Normalize absolute artifact path to repo-relative path when possible.
if [[ "$ARTIFACT_DIR" == "$WORKDIR/"* ]]; then
  ARTIFACT_DIR=".${ARTIFACT_DIR#$WORKDIR}"
fi

echo "[pipeline] validating artifact: $ARTIFACT_DIR"
./scripts/mongo_backup_validate.sh "$ARTIFACT_DIR"

echo "[pipeline] packaging artifact"
./scripts/mongo_backup_package.sh --artifact "$ARTIFACT_DIR"

BACKUP_ID="$(basename "$ARTIFACT_DIR")"
PACKAGE_FILE="$WORKDIR/backups/mongo_backup_${BACKUP_ID}.tar.gz"
if [[ ! -f "$PACKAGE_FILE" ]]; then
  echo "[pipeline] ERROR: expected package not found: $PACKAGE_FILE" >&2
  exit 1
fi

echo "[pipeline] package ready: $PACKAGE_FILE"

if [[ -n "$DRIVE_FOLDER_ID" ]]; then
  echo "[pipeline] Drive upload+verify enabled for folder: $DRIVE_FOLDER_ID"
  python3 ./scripts/mongo_backup_drive.py upload-and-verify \
    --file "$PACKAGE_FILE" \
    --folder-id "$DRIVE_FOLDER_ID"

  echo "[pipeline] Drive retention cleanup enabled"
  python3 ./scripts/mongo_backup_drive.py retention \
    --folder-id "$DRIVE_FOLDER_ID" \
    --keep-days "$DRIVE_RETENTION_DAYS" \
    --keep-min "$DRIVE_RETENTION_KEEP_MIN"
elif [[ -n "$BACKUP_UPLOAD_CMD" ]]; then
  echo "[pipeline] custom upload hook enabled"
  if [[ -n "$BACKUP_UPLOAD_TARGET" ]]; then
    # shellcheck disable=SC2086
    $BACKUP_UPLOAD_CMD "$PACKAGE_FILE" "$BACKUP_UPLOAD_TARGET/$(basename "$PACKAGE_FILE")"
  else
    # shellcheck disable=SC2086
    $BACKUP_UPLOAD_CMD "$PACKAGE_FILE"
  fi
  echo "[pipeline] custom upload hook completed"
else
  echo "[pipeline] upload step skipped (no DRIVE_FOLDER_ID or BACKUP_UPLOAD_CMD set)"
fi

echo "[pipeline] running retention cleanup"
./scripts/mongo_backup_retention.sh

echo "[pipeline] completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
