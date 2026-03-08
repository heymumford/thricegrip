#!/usr/bin/env bash
set -euo pipefail

OWNER="${GH_OWNER:-heymumford}"
RETRIES="${GH_RETRY_ATTEMPTS:-4}"
OWNER_REPO="${OWNER%/*}"
if [[ "$OWNER_REPO" != "$OWNER" ]]; then
  OWNER="$OWNER_REPO"
fi

usage() {
  cat <<'EOF'
Usage:
  gh-org-ci-lens.sh [repo...]

Environment:
  GH_OWNER           GitHub org/user owning repos (default: heymumford)
  GH_RETRY_ATTEMPTS   Retry count for transient failures (default: 4)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

run_api_with_retry() {
  local endpoint="$1"
  local attempt=1
  local sleep_sec=1
  while (( attempt <= RETRIES )); do
    if out="$(gh api "$endpoint" --jq '.total_count' 2>&1)"; then
      echo "$out"
      return 0
    fi
    if (( attempt == RETRIES )); then
      echo "FAILED:${out}" >&2
      return 1
    fi
    sleep "$sleep_sec"
    attempt=$((attempt+1))
    sleep_sec=$((sleep_sec*2))
  done
}

mapfile -t repos < <(
  if [[ $# -gt 0 ]]; then
    printf '%s\n' "$@"
  else
    gh repo list "$OWNER" --limit 200 --json nameWithOwner --jq '.[].nameWithOwner' \
      | sed "s#^$OWNER/##"
  fi
)

printf "repo,status,total_runs,error\n"
for repo in "${repos[@]}"; do
  [[ -n "$repo" ]] || continue
  if out="$(run_api_with_retry "/repos/$OWNER/$repo/actions/runs")"; then
    printf "%s,ok,%s,\n" "$repo" "$out"
  else
    printf "%s,failed,,%q\n" "$repo" "$out"
  fi
done

