#!/usr/bin/env bash
set -euo pipefail

WORKDIR="${WORKDIR:-$(pwd)}"
BACKUP_ROOT="${BACKUP_ROOT:-$WORKDIR/backups/mongo}"
PACKAGE_ROOT="${PACKAGE_ROOT:-$WORKDIR/backups}"

# Keep artifact directories for N days (based on mtime)
RETAIN_ARTIFACT_DAYS="${RETAIN_ARTIFACT_DAYS:-14}"
# Keep packaged tar.gz files for N days
RETAIN_PACKAGE_DAYS="${RETAIN_PACKAGE_DAYS:-30}"

if [[ -d "$BACKUP_ROOT" ]]; then
  echo "[retention] pruning artifact dirs older than $RETAIN_ARTIFACT_DAYS days in $BACKUP_ROOT"
  find "$BACKUP_ROOT" -mindepth 4 -maxdepth 4 -type d -mtime "+$RETAIN_ARTIFACT_DAYS" -print -exec rm -rf {} +

  # Remove empty day/month/year directories after pruning
  find "$BACKUP_ROOT" -type d -empty -print -delete
fi

if [[ -d "$PACKAGE_ROOT" ]]; then
  echo "[retention] pruning packaged archives older than $RETAIN_PACKAGE_DAYS days in $PACKAGE_ROOT"
  find "$PACKAGE_ROOT" -maxdepth 1 -type f -name 'mongo_backup_*.tar.gz' -mtime "+$RETAIN_PACKAGE_DAYS" -print -delete
fi

echo "[retention] done"
