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

if [[ -n "$BACKUP_UPLOAD_CMD" ]]; then
  echo "[pipeline] upload step enabled"
  if [[ -n "$BACKUP_UPLOAD_TARGET" ]]; then
    # shellcheck disable=SC2086
    $BACKUP_UPLOAD_CMD "$PACKAGE_FILE" "$BACKUP_UPLOAD_TARGET/$(basename "$PACKAGE_FILE")"
  else
    # shellcheck disable=SC2086
    $BACKUP_UPLOAD_CMD "$PACKAGE_FILE"
  fi
  echo "[pipeline] upload step completed"
else
  echo "[pipeline] upload step skipped (BACKUP_UPLOAD_CMD not set)"
fi

echo "[pipeline] running retention cleanup"
./scripts/mongo_backup_retention.sh

echo "[pipeline] completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
