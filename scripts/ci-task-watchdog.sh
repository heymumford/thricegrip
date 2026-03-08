#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/ci-task-watchdog.sh "<task-label>" <command> [args...]

Example:
  scripts/ci-task-watchdog.sh "deploy::flyctl" flyctl deploy --remote-only
EOF
}

if [ "$#" -lt 2 ]; then
  usage
  exit 64
fi

TASK_LABEL="$1"
shift

MAX_SECONDS="${CI_MONITOR_MAX_SECONDS:-300}"
if ! [[ "${MAX_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "CI_MONITOR_MAX_SECONDS must be a positive integer. Got: ${MAX_SECONDS}" >&2
  exit 65
fi

FAIL_ON_SLOW="${CI_MONITOR_FAIL_ON_SLOW:-0}"
LOG_DIR="${CI_MONITOR_LOG_DIR:-.ci-monitor}"
LOG_FILE="${CI_MONITOR_LOG_FILE:-${LOG_DIR}/task-runtimes.tsv}"
START_TS="$(date +%s)"
TASK_START_ISO="$(date -u +%FT%TZ)"

set +e
"$@"
TASK_EXIT_CODE=$?
set -e

END_TS="$(date +%s)"
ELAPSED_SECONDS="$((END_TS - START_TS))"
REPO="${GITHUB_REPOSITORY:-local}"
RUN_ID="${GITHUB_RUN_ID:-manual}"
REF="${GITHUB_REF:-local}"
HOSTNAME="${HOSTNAME:-unknown}"

mkdir -p "$LOG_DIR"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$TASK_START_ISO" \
  "$TASK_LABEL" \
  "$ELAPSED_SECONDS" \
  "$MAX_SECONDS" \
  "$TASK_EXIT_CODE" \
  "$REF" \
  "$RUN_ID" \
  "$REPO" \
  "$HOSTNAME" >> "$LOG_FILE"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  SAFE_KEY="$(printf '%s' "$TASK_LABEL" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_' | sed 's/^_\\{1,\\}//;s/_\\{1,\\}$//' | sed 's/\\.{2,}/_/g')"
  echo "${SAFE_KEY}_seconds=${ELAPSED_SECONDS}" >> "$GITHUB_OUTPUT"
  echo "${SAFE_KEY}_exit_code=${TASK_EXIT_CODE}" >> "$GITHUB_OUTPUT"
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### CI Task Watchdog"
    echo "| Task | Duration | Budget | Exit | Repository |"
    echo "|---|---:|---:|---:|---|"
    echo "| ${TASK_LABEL} | ${ELAPSED_SECONDS}s | ${MAX_SECONDS}s | ${TASK_EXIT_CODE} | ${REPO} |"
  } >> "${GITHUB_STEP_SUMMARY}"
fi

if [ "${ELAPSED_SECONDS}" -gt "${MAX_SECONDS}" ]; then
  echo "::warning file=ci-task-watchdog.sh,line=1::[ci-task-watchdog] ${TASK_LABEL} took ${ELAPSED_SECONDS}s, exceeding ${MAX_SECONDS}s budget."
  echo "Refactor signal: split ${TASK_LABEL} into smaller async or sharded tasks."
  if [ "${FAIL_ON_SLOW}" = "1" ]; then
    if [ "${TASK_EXIT_CODE}" -eq 0 ]; then
      echo "::error file=ci-task-watchdog.sh,line=1::[ci-task-watchdog] Budget exceeded and action marked required. Investigate and refactor ${TASK_LABEL}."
      exit 88
    fi
  fi
fi

exit "${TASK_EXIT_CODE}"
