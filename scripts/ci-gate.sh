#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
REPO_ROOT="${2:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

UV_SYNC_ARGS="${CI_GATE_UV_SYNC_ARGS:---all-extras}"
PYTEST_PATH="${CI_GATE_PYTEST_PATH:-tests/}"
PYTEST_ARGS="${CI_GATE_PYTEST_ARGS:--cache-clear -q}"
SECURITY_FAIL_ON_FINDINGS="${CI_GATE_SECURITY_FAIL_ON_FINDINGS:-0}"

cd "$REPO_ROOT"

require_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "FATAL: uv is required on PATH for ci-gate"
    exit 1
  fi
}

run_meta_checks() {
  local meta_script="$REPO_ROOT/scripts/verify-meta-invariants.sh"
  local contract_script="$REPO_ROOT/scripts/verify-host-service-contract.sh"
  local strict_contract="${CI_GATE_REQUIRE_HOST_CONTRACT:-0}"

  if [[ -x "$meta_script" ]]; then
    "$meta_script"
  elif [[ -f "$meta_script" ]]; then
    bash "$meta_script"
  fi

  if [[ -x "$contract_script" ]]; then
    if [[ "$strict_contract" == "1" ]]; then
      "$contract_script"
    else
      "$contract_script" || echo "::warning::Host-service contract check failed; set CI_GATE_REQUIRE_HOST_CONTRACT=1 for strict mode."
    fi
  elif [[ -f "$contract_script" ]]; then
    if [[ "$strict_contract" == "1" ]]; then
      bash "$contract_script"
    else
      bash "$contract_script" || echo "::warning::Host-service contract check failed; set CI_GATE_REQUIRE_HOST_CONTRACT=1 for strict mode."
    fi
  fi
}

run_sync() {
  uv sync ${UV_SYNC_ARGS}
}

run_lint() {
  run_meta_checks
  run_sync

  local paths=( )
  [[ -d "$REPO_ROOT/src" ]] && paths+=("$REPO_ROOT/src")
  [[ -d "$REPO_ROOT/tests" ]] && paths+=("$REPO_ROOT/tests")

  if (( ${#paths[@]} == 0 )); then
    echo "No src/ or tests/ directories detected, skipping ruff checks"
    return
  fi

  uv run ruff check "${paths[@]}"
  uv run ruff format --check --diff "${paths[@]}"
}

run_test() {
  if [[ ! -d "$REPO_ROOT/tests" ]]; then
    echo "No tests/ directory; skipping test run"
    return
  fi

  run_sync
  uv run pytest ${PYTEST_ARGS} "$PYTEST_PATH"
}

run_security() {
  local req_file="/tmp/ci-gate-${RANDOM:-$$}.txt"
  local audit_log="/tmp/pip-audit-${RANDOM:-$$}.log"
  local security_status=0
  local has_findings=0

  run_sync
  uv export --no-hashes --no-emit-project > "$req_file"
  if ! uv pip install --no-deps pip-audit >/tmp/pip-audit-install.log 2>&1; then
    echo "::warning::pip-audit installation unavailable; attempting audit with existing toolchain"
  fi

  run_pip_audit() {
    local req_path="$1"
    local log_path="$2"
    local status=0
    local module_status=0

    set +e
    uv run pip-audit -r "$req_path" --no-deps >"$log_path" 2>&1
    status=$?
    if [[ "$status" -ne 0 ]]; then
      echo "::warning::Primary pip-audit invocation failed with status $status; retrying via module path."
      uv run python -m pip_audit -r "$req_path" --no-deps >>"$log_path" 2>&1
      module_status=$?
      status=$module_status
    fi
    set -e

    return "$status"
  }

  if ! run_pip_audit "$req_file" "$audit_log"; then
    security_status=$?
  fi

  if [[ "$security_status" -eq 1 ]] && grep -Eqi "vulnerability|vulnerabilities|cve-[0-9]{4}-[0-9]{4,}" "$audit_log"; then
    has_findings=1
  fi

  if [[ "$security_status" -ne 0 ]]; then
    if [[ "$security_status" -eq 1 ]]; then
      if [[ "$has_findings" == "1" ]]; then
        echo "::warning::pip-audit found advisories; review before promotion"
      else
        echo "::error::pip-audit returned exit 1 without advisory output; see $audit_log"
      fi
    else
      echo "::error::pip-audit execution failed (exit $security_status); see $audit_log"
    fi
  fi

  if [[ "$security_status" -eq 1 && "$has_findings" -eq 0 ]]; then
    security_status=2
  fi

  rm -f "$req_file" "$audit_log"

  if [[ "${SECURITY_FAIL_ON_FINDINGS}" == "1" ]]; then
    if [[ "$security_status" -eq 1 ]] && [[ "$has_findings" -eq 0 ]]; then
      return 2
    fi
    return "$security_status"
  fi
  return 0
}

require_uv

case "$MODE" in
  lint)
    run_lint
    ;;
  test)
    run_test
    ;;
  security)
    run_security
    ;;
  full|all)
    run_lint
    run_test
    run_security
    ;;
  *)
    echo "Usage: $(basename "$0") <lint|test|security|all> [repo-root]"
    exit 2
    ;;
esac
