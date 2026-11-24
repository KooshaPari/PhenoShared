#!/usr/bin/env bash
# forge-net-heal.sh — host-side network connectivity healer (v0.12 phase 3).
#
# Checks DNS resolution for 5 critical hosts and TCP reachability for 8
# critical endpoints. Installed at ~/.forge/bin/forge-net-heal.sh and
# invoked by the com.phenoforge.forge-net-heal launchd plist with the
# `check` subcommand.
#
# Subcommands:
#   status  — list 5 DNS hosts + 8 TCP endpoints with their last status.
#   check   — exit 0 if all reachable, exit 1 otherwise (also logs).
#   report  — markdown table of the last check.
#
# Critical hosts (WBS-PERT-100 v0.12 task 42):
#   github.com, pypi.org, anthropic.com, openai.com, huggingface.co
#
# Critical endpoints (WBS-PERT-100 v0.12 task 43):
#   1.1.1.1:443    Cloudflare HTTPS
#   8.8.8.8:53     Google DNS
#   github.com:443 GitHub HTTPS
#   pypi.org:443   PyPI HTTPS
#   anthropic.com:443 Anthropic HTTPS
#   openai.com:443 OpenAI HTTPS
#   huggingface.co:443 HF HTTPS
#   1.0.0.1:53     Cloudflare DNS (secondary)
#
# Exit codes:
#   0 = all reachable
#   1 = at least one unreachable
#   2 = invocation error

set -uo pipefail

readonly DNS_HOSTS=(
  "github.com"
  "pypi.org"
  "anthropic.com"
  "openai.com"
  "huggingface.co"
)

# "host port label" triples
readonly TCP_ENDPOINTS=(
  "1.1.1.1 443 Cloudflare-HTTPS"
  "8.8.8.8 53 Google-DNS"
  "github.com 443 GitHub-HTTPS"
  "pypi.org 443 PyPI-HTTPS"
  "anthropic.com 443 Anthropic-HTTPS"
  "openai.com 443 OpenAI-HTTPS"
  "huggingface.co 443 HuggingFace-HTTPS"
  "1.0.0.1 53 Cloudflare-DNS-secondary"
)

STATE_FILE="${HOME}/.pheno-harness/state/forge-net-heal.last"
mkdir -p "$(dirname "${STATE_FILE}")"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

usage() {
  cat <<USAGE
forge-net-heal.sh — host-side network connectivity healer

Usage:
  forge-net-heal.sh status   # list DNS hosts + TCP endpoints with status
  forge-net-heal.sh check    # probe all hosts; exit 1 if any unreachable
  forge-net-heal.sh report   # markdown table of last check
USAGE
}

# Probe a single DNS host. Echoes "ok" or "fail".
probe_dns() {
  local host="$1"
  if dscacheutil -q host -a name "${host}" >/dev/null 2>&1 \
     || (command -v host >/dev/null && host -W 3 "${host}" >/dev/null 2>&1) \
     || getent hosts "${host}" >/dev/null 2>&1 \
     || python3 -c "import socket,sys; socket.getaddrinfo('${host}', None)" >/dev/null 2>&1; then
    printf 'ok'
  else
    printf 'fail'
  fi
}

# Probe a single TCP endpoint. Echoes "ok" or "fail".
probe_tcp() {
  local host="$1" port="$2"
  if nc -z -w 3 "${host}" "${port}" 2>/dev/null; then
    printf 'ok'
  else
    printf 'fail'
  fi
}

# --- status sub-command -------------------------------------------------
cmd_status() {
  echo "=== forge-net-heal status ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  echo
  echo "DNS hosts (${#DNS_HOSTS[@]}):"
  for host in "${DNS_HOSTS[@]}"; do
    printf '  %-20s %s\n' "${host}" "$(probe_dns "${host}")"
  done
  echo
  echo "TCP endpoints (${#TCP_ENDPOINTS[@]}):"
  for ep in "${TCP_ENDPOINTS[@]}"; do
    read -r host port label <<<"${ep}"
    printf '  %-32s %-6s %s\n' "${label}" "${host}:${port}" "$(probe_tcp "${host}" "${port}")"
  done
}

# --- check sub-command --------------------------------------------------
cmd_check() {
  local exit_code=0
  local dns_fail=0 tcp_fail=0

  log "net-heal check: starting (${#DNS_HOSTS[@]} DNS, ${#TCP_ENDPOINTS[@]} TCP)"

  for host in "${DNS_HOSTS[@]}"; do
    local status
    status=$(probe_dns "${host}")
    if [ "${status}" = "ok" ]; then
      log "OK DNS ${host}"
    else
      log "WARN DNS ${host} unreachable"
      dns_fail=$((dns_fail + 1))
      exit_code=1
    fi
  done

  for ep in "${TCP_ENDPOINTS[@]}"; do
    read -r host port label <<<"${ep}"
    local status
    status=$(probe_tcp "${host}" "${port}")
    if [ "${status}" = "ok" ]; then
      log "OK TCP ${label} ${host}:${port}"
    else
      log "WARN TCP ${label} ${host}:${port} unreachable"
      tcp_fail=$((tcp_fail + 1))
      exit_code=1
    fi
  done

  # Record last-check state for `report`
  {
    printf 'timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'dns_fail=%s\n' "${dns_fail}"
    printf 'tcp_fail=%s\n' "${tcp_fail}"
    for host in "${DNS_HOSTS[@]}"; do
      printf 'dns|%s|%s\n' "${host}" "$(probe_dns "${host}")"
    done
    for ep in "${TCP_ENDPOINTS[@]}"; do
      read -r host port label <<<"${ep}"
      printf 'tcp|%s|%s:%s|%s\n' "${label}" "${host}" "${port}" "$(probe_tcp "${host}" "${port}")"
    done
  } > "${STATE_FILE}"

  if [ "${exit_code}" -eq 0 ]; then
    log "net-heal: all endpoints reachable"
  else
    log "net-heal: ${dns_fail} DNS + ${tcp_fail} TCP failures (heal recommended)"
  fi

  return "${exit_code}"
}

# --- report sub-command -------------------------------------------------
cmd_report() {
  if [ ! -f "${STATE_FILE}" ]; then
    echo "# forge-net-heal report"
    echo
    echo "No prior check recorded. Run \`forge-net-heal.sh check\` first."
    return 0
  fi

  local ts dns_fail tcp_fail overall
  ts=$(awk -F= '/^timestamp=/ {print $2}' "${STATE_FILE}")
  dns_fail=$(awk -F= '/^dns_fail=/ {print $2}' "${STATE_FILE}")
  tcp_fail=$(awk -F= '/^tcp_fail=/ {print $2}' "${STATE_FILE}")
  if [ "${dns_fail}" -eq 0 ] && [ "${tcp_fail}" -eq 0 ]; then
    overall="HEALTHY"
  else
    overall="DEGRADED"
  fi

  cat <<MD
# forge-net-heal report — ${ts}

## Summary

| Metric | Failures |
|--------|----------|
| DNS hosts | ${dns_fail} / ${#DNS_HOSTS[@]} |
| TCP endpoints | ${tcp_fail} / ${#TCP_ENDPOINTS[@]} |

**Overall:** ${overall}

## DNS hosts

| Host | Status |
|------|--------|
MD

  awk -F'|' '/^dns\|/ {printf "| %s | %s |\n", $2, $3}' "${STATE_FILE}"

  cat <<MD

## TCP endpoints

| Endpoint | Address | Status |
|----------|---------|--------|
MD

  awk -F'|' '/^tcp\|/ {printf "| %s | %s | %s |\n", $2, $3, $4}' "${STATE_FILE}"
}

# --- dispatch -----------------------------------------------------------
case "${1:-status}" in
  status) cmd_status ;;
  check)  cmd_check ;;
  report) cmd_report ;;
  -h|--help|help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
