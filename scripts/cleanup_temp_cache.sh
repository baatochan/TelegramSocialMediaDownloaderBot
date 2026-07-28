#!/usr/bin/env bash
set -euo pipefail

# Manual run:
#   /path/to/repo/scripts/cleanup_temp_cache.sh
# Intended schedule: once daily around 03:00 local server time.
# Example cron:
#   0 3 * * * /path/to/repo/scripts/cleanup_temp_cache.sh >> /path/to/repo/logs/cleanup_temp_cache.log 2>&1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TEMP_DIR="${REPO_DIR}/temp"

MAX_TOTAL_BYTES=5368709120 # 5 GiB
MAX_FILE_SIZE_MB=100       # 100 MiB
GRACE_MINUTES=120          # keep recently created/modified files

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') cleanup: $*"
}

get_total_bytes() {
    local total
    total="$(du -sb "${TEMP_DIR}" 2>/dev/null | awk '{print $1}')"
    if [[ -z "${total}" ]]; then
        echo 0
        return
    fi
    echo "${total}"
}

if [[ ! -d "${TEMP_DIR}" ]]; then
    log "skipped (missing temp dir: ${TEMP_DIR})"
    exit 0
fi

log "start temp_dir=${TEMP_DIR}"
initial_bytes="$(get_total_bytes)"

# Phase 1: remove files bigger than 100MB, excluding grace-window files.
find "${TEMP_DIR}" -type f -mmin +"${GRACE_MINUTES}" -size +"${MAX_FILE_SIZE_MB}"M -delete

# Phase 2: remove files older than 14 days, excluding grace-window files.
find "${TEMP_DIR}" -type f -mmin +"${GRACE_MINUTES}" -mtime +13 -delete

current_bytes="$(get_total_bytes)"
if (( current_bytes > MAX_TOTAL_BYTES )); then
    # Phase 3: if still above cap, remove files older than 7 days.
    find "${TEMP_DIR}" -type f -mmin +"${GRACE_MINUTES}" -mtime +6 -delete
fi

current_bytes="$(get_total_bytes)"
if (( current_bytes > MAX_TOTAL_BYTES )); then
    # Phase 4: if still above cap, remove files older than 1 day.
    find "${TEMP_DIR}" -type f -mmin +"${GRACE_MINUTES}" -mtime +0 -delete
fi

final_bytes="$(get_total_bytes)"

log "done initial_bytes=${initial_bytes} final_bytes=${final_bytes}"

if (( final_bytes > MAX_TOTAL_BYTES )); then
    log "WARNING final cache size still above cap (${final_bytes} > ${MAX_TOTAL_BYTES})"
fi
