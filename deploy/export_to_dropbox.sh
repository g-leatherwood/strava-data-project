#!/usr/bin/env bash
# Export every activity to CSV and upload it to Dropbox with rclone,
# overwriting the same file each run. Meant for a daily cron job chained after
# the ETL, so it only runs when the load succeeded.
set -euo pipefail

# Overridable from the environment; the defaults match the droplet setup.
STRAVA_CLI="${STRAVA_CLI:-$HOME/bin/strava-cli}"
DROPBOX_DEST="${DROPBOX_DEST:-dropbox:strava_all.csv}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }
trap 'log ERROR "Dropbox export failed"' ERR

# Write locally first so Dropbox never receives a half-written file.
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

# strava-cli reads DATABASE_URL_NEON from ~/.config/strava-cli/.env.
"$STRAVA_CLI" --out "$tmp"
rclone copyto "$tmp" "$DROPBOX_DEST"
log INFO "Exported activities to $DROPBOX_DEST"
