#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<USAGE
Usage:
  ./scripts/install_mongo_backup_cron.sh

Optional env vars:
  WORKDIR        Repo root path (default: current directory)
  CRON_SCHEDULE  Cron schedule expression (default: 15 2 * * *)
USAGE
  exit 0
fi

WORKDIR="${WORKDIR:-$(pwd)}"
CRON_SCHEDULE="${CRON_SCHEDULE:-15 2 * * *}"
TAG="# juicyfruit-mongo-backup-pipeline"
LINE="$CRON_SCHEDULE cd $WORKDIR && ./scripts/mongo_backup_pipeline.sh >> $WORKDIR/logs/mongo_backup_pipeline.log 2>&1 $TAG"

mkdir -p "$WORKDIR/logs"
TMPFILE="$(mktemp)"

crontab -l 2>/dev/null | grep -v "$TAG" > "$TMPFILE" || true
echo "$LINE" >> "$TMPFILE"
crontab "$TMPFILE"
rm -f "$TMPFILE"

echo "Cron installed: $LINE"
echo "View cron: crontab -l | rg juicyfruit-mongo-backup-pipeline"
