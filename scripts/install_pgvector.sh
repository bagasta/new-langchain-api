#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: DATABASE_URL=postgresql://user:pass@host:5432/db \ 
       scripts/install_pgvector.sh

Installs the pgvector extension package (if possible) and enables it in the
specified database. Provide DATABASE_URL via environment variable or as the
first argument.
USAGE
}

get_database_url() {
  if [[ -n "${1:-}" ]]; then
    echo "$1"
  elif [[ -n "${DATABASE_URL:-}" ]]; then
    echo "$DATABASE_URL"
  else
    return 1
  fi
}

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
  elif command -v yum >/dev/null 2>&1; then
    echo "yum"
  elif command -v dnf >/dev/null 2>&1; then
    echo "dnf"
  elif command -v pacman >/dev/null 2>&1; then
    echo "pacman"
  elif command -v brew >/dev/null 2>&1; then
    echo "brew"
  else
    echo "unknown"
  fi
}

install_extension_package() {
  local manager="$1"
  local pg_major
  pg_major=$(psql -V 2>/dev/null | awk '{print $3}' | cut -d. -f1 || true)

  case "$manager" in
    apt)
      sudo apt-get update
      if [[ -n "$pg_major" ]]; then
        if sudo apt-get install -y "postgresql-${pg_major}-pgvector"; then
          return 0
        fi
      fi
      if sudo apt-get install -y postgresql-16-pgvector postgresql-15-pgvector 2>/dev/null; then
        return 0
      fi
      ;;
    yum|dnf)
      if sudo "$manager" install -y pgvector; then
        return 0
      fi
      ;;
    pacman)
      if sudo pacman -Sy --noconfirm pgvector; then
        return 0
      fi
      ;;
    brew)
      if brew list pgvector >/dev/null 2>&1; then
        return 0
      fi
      if brew install pgvector; then
        return 0
      fi
      ;;
  esac

  echo "Unable to install pgvector automatically. Install it manually for your PostgreSQL distribution." >&2
  return 1
}

create_extension() {
  local db_url="$1"
  if ! command -v psql >/dev/null 2>&1; then
    echo "psql command not found. Install PostgreSQL client tools first." >&2
    return 1
  fi

  if ! PGPASSWORD="${PGPASSWORD:-}" psql "$db_url" -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS vector;'; then
    echo "Failed to create extension. Ensure the server package is installed and you have the required privileges." >&2
    return 1
  fi

  echo "pgvector extension is ready."
}

main() {
  local db_url
  db_url=$(get_database_url "${1:-}") || {
    usage
    exit 1
  }

  echo "Using database: $db_url"

  local manager
  manager=$(detect_package_manager)
  if ! install_extension_package "$manager"; then
    echo "Continuing without automatic package install." >&2
  fi

  if create_extension "$db_url"; then
    exit 0
  fi

  echo "If the extension is still unavailable, install the server package manually and rerun this script." >&2
  exit 1
}

main "$@"
