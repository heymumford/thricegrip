#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_FILE="$ROOT_DIR/invariant-policy.md"

if [[ ! -f "$POLICY_FILE" ]]; then
  echo "FATAL: Missing policy file: $POLICY_FILE"
  exit 1
fi

STATUS=0

if [[ $# -eq 0 ]]; then
  SEARCH_DIR="$ROOT_DIR"
elif [[ "$1" == "--repo" ]]; then
  if [[ $# -ne 2 ]]; then
    echo "Usage: $0 [--repo /path/to/repo]"
    exit 2
  fi
  SEARCH_DIR="$2"
else
  echo "Usage: $0 [--repo /path/to/repo]"
  exit 2
fi

if [[ ! -d "$SEARCH_DIR" ]]; then
  echo "FATAL: Search directory does not exist: $SEARCH_DIR"
  exit 1
fi

require_meta_section() {
  local file_path="$1"
  if ! grep -q "Meta-Architectural Operating Lens" "$file_path"; then
    echo "MISSING meta section: $file_path"
    STATUS=1
  else
    echo "OK: $file_path"
  fi
}

while IFS= read -r instruction_file; do
  if [[ -f "$instruction_file" ]]; then
    require_meta_section "$instruction_file"
  fi
done < <(find "$SEARCH_DIR" -mindepth 2 -maxdepth 3 -type f \( -name AGENTS.md -o -name CLAUDE.md \) )

if [[ $STATUS -eq 0 ]]; then
  echo "All discovered instruction files include Meta-Architectural Operating Lens."
fi

exit $STATUS
