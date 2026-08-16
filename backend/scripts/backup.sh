#!/usr/bin/env bash
# Backup script: database dump + storage archive.
# Usage: ./scripts/backup.sh [output-dir]
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-$BASE_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

if [ -n "${DATABASE_URL:-}" ] && [[ "$DATABASE_URL" == postgresql* ]]; then
  echo "PostgreSQL detected; use pg_dump:"
  echo "  pg_dump \"$DATABASE_URL\" | gzip > \"$OUT_DIR/db_$STAMP.sql.gz\""
else
  if [ -f "$BASE_DIR/data/app.db" ]; then
    cp "$BASE_DIR/data/app.db" "$OUT_DIR/app_$STAMP.db"
    echo "backed up sqlite -> $OUT_DIR/app_$STAMP.db"
  fi
fi

if [ -d "$BASE_DIR/data/storage" ]; then
  tar -czf "$OUT_DIR/storage_$STAMP.tar.gz" -C "$BASE_DIR/data" storage
  echo "backed up storage -> $OUT_DIR/storage_$STAMP.tar.gz"
fi

if [ -f "$BASE_DIR/data/vector_store.sqlite" ]; then
  cp "$BASE_DIR/data/vector_store.sqlite" "$OUT_DIR/vector_$STAMP.sqlite"
  echo "backed up vector store -> $OUT_DIR/vector_$STAMP.sqlite"
fi

echo "backup complete in $OUT_DIR"