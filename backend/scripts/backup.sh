#!/bin/sh
set -eu

: "${APP_DATABASE_URL:?APP_DATABASE_URL is required}"
: "${APP_STORAGE_ROOT:=data/storage}"
: "${BACKUP_ROOT:=data/backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
destination="$BACKUP_ROOT/$timestamp"
mkdir -p "$destination"

case "$APP_DATABASE_URL" in
  postgresql*|postgres*)
    pg_dump "$APP_DATABASE_URL" --format=custom --file="$destination/database.dump"
    ;;
  sqlite*)
    database_path=${APP_DATABASE_URL##*///}
    cp "$database_path" "$destination/database.sqlite"
    ;;
  *)
    echo "Unsupported database scheme" >&2
    exit 1
    ;;
esac

tar -czf "$destination/object-storage.tar.gz" -C "$APP_STORAGE_ROOT" .
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+$BACKUP_RETENTION_DAYS" -exec rm -rf {} \;
echo "$destination"
