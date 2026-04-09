#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<USAGE
Usage:
  ./scripts/install_mongo_backup_systemd_timer.sh

Optional env vars:
  WORKDIR        Repo root path (default: current directory)
  SCHEDULE_UTC   Timer schedule in UTC HH:MM:SS (default: 02:15:00)
USAGE
  exit 0
fi

WORKDIR="${WORKDIR:-$(pwd)}"
SCHEDULE_UTC="${SCHEDULE_UTC:-02:15:00}"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="juicyfruit-mongo-backup.service"
TIMER_NAME="juicyfruit-mongo-backup.timer"
ENV_FILE_PATH="${WORKDIR}/scripts/mongo_backup_pipeline.env"

mkdir -p "$USER_SYSTEMD_DIR" "$WORKDIR/logs"

cat > "$USER_SYSTEMD_DIR/$SERVICE_NAME" <<SERVICE
[Unit]
Description=JuicyFruit Mongo backup pipeline

[Service]
Type=oneshot
WorkingDirectory=$WORKDIR
ExecStart=$WORKDIR/scripts/mongo_backup_pipeline.sh
Environment=WORKDIR=$WORKDIR
EnvironmentFile=-$ENV_FILE_PATH
StandardOutput=append:$WORKDIR/logs/mongo_backup_pipeline.log
StandardError=append:$WORKDIR/logs/mongo_backup_pipeline.log
SERVICE

cat > "$USER_SYSTEMD_DIR/$TIMER_NAME" <<TIMER
[Unit]
Description=Run JuicyFruit Mongo backup daily

[Timer]
OnCalendar=*-*-* $SCHEDULE_UTC
Persistent=true
Unit=$SERVICE_NAME

[Install]
WantedBy=timers.target
TIMER

if ! command -v systemctl >/dev/null 2>&1; then
  echo "ERROR: systemctl not found. Use cron installer instead." >&2
  exit 1
fi

systemctl --user daemon-reload
systemctl --user enable --now "$TIMER_NAME"

echo "Installed and started $TIMER_NAME"
echo "Check status: systemctl --user status $TIMER_NAME"
echo "List timers : systemctl --user list-timers | rg juicyfruit-mongo-backup"
echo "Optional env file: $ENV_FILE_PATH"
