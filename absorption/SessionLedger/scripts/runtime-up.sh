#!/usr/bin/env bash
# SessionLedger runtime facade — bring up daemon (+ viewer when native).
# Default: process-compose (zero hard deps beyond that CLI).
# Optional engines via SL_RUNTIME: process-compose|pheno|podman|wsl|apple|container
# See docs/ops/runtime-facade.md. ADR 0001: no tray / resident companion.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

info() { printf '[runtime-up] %s\n' "$*"; }
err() { printf '[runtime-up] %s\n' "$*" >&2; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

show_engine_hints() {
  info 'engine probe:'
  if have_cmd process-compose; then
    printf '  - process-compose: available (default)\n'
  else
    printf '  - process-compose: missing — install https://github.com/F1bonacc1/process-compose\n'
  fi

  pheno=()
  have_cmd pheno-compose && pheno+=('pheno-compose')
  have_cmd nvms && pheno+=('nvms')
  if ((${#pheno[@]} > 0)); then
    printf '  - PhenoCompose/nvms: %s on PATH (SL_RUNTIME=pheno)\n' "${pheno[*]}"
  else
    printf '  - PhenoCompose/nvms: not on PATH (optional; see docs/ops/runtime-facade.md)\n'
  fi

  if have_cmd podman; then
    printf '  - podman: available (SL_RUNTIME=podman)\n'
  else
    printf '  - podman: not on PATH\n'
  fi

  if have_cmd wsl.exe || have_cmd wsl; then
    printf '  - WSL: wsl.exe available (SL_RUNTIME=wsl; primarily for Windows hosts)\n'
  else
    printf '  - WSL: wsl.exe not found\n'
  fi

  if have_cmd container; then
    printf '  - Apple Container: container CLI available (SL_RUNTIME=apple|container)\n'
  else
    printf '  - Apple Container: container CLI not found (macOS only)\n'
  fi
}

resolve_runtime() {
  local raw="${SL_RUNTIME:-process-compose}"
  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$raw" in
    process-compose|pc|default|'') echo process-compose ;;
    pheno|pheno-compose|phenocompose|nvms) echo pheno ;;
    podman) echo podman ;;
    wsl) echo wsl ;;
    apple|apple-container|container) echo apple ;;
    *)
      err "Unknown SL_RUNTIME='$SL_RUNTIME'. Use process-compose|pheno|podman|wsl|apple|container."
      exit 2
      ;;
  esac
}

invoke_process_compose() {
  if ! have_cmd process-compose; then
    err 'process-compose not found on PATH.'
    err ''
    err 'Install: https://github.com/F1bonacc1/process-compose'
    err '  macOS:  brew install f1bonacc1/tap/process-compose'
    err '  Or run crates manually:'
    err '    cargo run -p sl-daemon -- serve'
    err '    cargo run -p sl-viewer'
    err ''
    err 'This facade defaults to process-compose (ADR 0001: CLI/ops stack, no tray).'
    exit 1
  fi
  info "starting process-compose -f ${REPO_ROOT}/process-compose.yaml up"
  exec process-compose -f "${REPO_ROOT}/process-compose.yaml" up "$@"
}

invoke_pheno() {
  local cli=''
  if have_cmd pheno-compose; then
    cli=pheno-compose
  elif have_cmd nvms; then
    cli=nvms
  fi
  if [[ -z "$cli" ]]; then
    err 'SL_RUNTIME=pheno but neither pheno-compose nor nvms is on PATH.'
    err ''
    err 'Install (Phenotype / PhenoCompose):'
    err '  curl -fsSL https://get.nvms.dev | sh'
    err '  # or: cargo install pheno-compose --features nvms-driver'
    err '  # or: go build from https://github.com/KooshaPari/nvms'
    err ''
    err 'SessionLedger does not vendor PhenoCompose. Prefer process-compose for zero-dep local dev:'
    err '  SL_RUNTIME=process-compose ./scripts/runtime-up.sh'
    err ''
    err 'Stub compose (comment-only): compose/pheno-compose.yaml'
    err 'Docs: docs/ops/runtime-facade.md'
    exit 1
  fi

  local file_args=()
  local stub="${REPO_ROOT}/compose/pheno-compose.yaml"
  if [[ -f "$stub" ]]; then
    file_args=(-f "$stub")
    info "using stub/config $stub (see comments inside for Phenotype alignment)"
  fi

  info "delegating to $cli ${file_args[*]+${file_args[*]}} up"
  set +e
  "$cli" "${file_args[@]}" up "$@"
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    err "$cli exited with code $rc."
    err "If the CLI does not accept 'up' yet, use process-compose:"
    err '  SL_RUNTIME=process-compose ./scripts/runtime-up.sh'
    err 'Or follow PhenoCompose/nvms docs for the current compose subcommand.'
    exit "$rc"
  fi
  exit 0
}

invoke_podman() {
  if ! have_cmd podman; then
    err 'SL_RUNTIME=podman but podman is not on PATH.'
    err ''
    err 'Install Podman, then re-run, or fall back:'
    err '  SL_RUNTIME=process-compose ./scripts/runtime-up.sh'
    exit 1
  fi

  local cf="${REPO_ROOT}/Containerfile"
  if [[ ! -f "$cf" ]]; then
    cf="${REPO_ROOT}/crates/sl-daemon/Containerfile"
  fi
  if [[ ! -f "$cf" ]]; then
    err 'No Containerfile found at repo root or crates/sl-daemon/Containerfile.'
    exit 1
  fi

  if have_cmd podman-compose; then
    local pcf="${REPO_ROOT}/compose/podman-compose.yaml"
    if [[ -f "$pcf" ]]; then
      info "podman-compose -f $pcf up"
      exec podman-compose -f "$pcf" up "$@"
    fi
    info 'podman-compose on PATH but compose/podman-compose.yaml missing; using podman build/run'
  fi

  local image="${SL_PODMAN_IMAGE:-sl-daemon:local}"
  local data="${REPO_ROOT}/.sl-data"
  mkdir -p "${data}/sessions" "${data}/out"
  local port="${SL_PORT:-8080}"

  info "podman build -t $image -f $cf ."
  podman build -t "$image" -f "$cf" .
  info "podman run --rm -p ${port}:8080 -v ${data}:/data $image"
  exec podman run --rm \
    -p "${port}:8080" \
    -v "${data}:/data" \
    -e SL_DATA_DIR=/data \
    -e SL_PORT=8080 \
    "$image" "$@"
}

invoke_wsl() {
  local wsl=''
  if have_cmd wsl.exe; then
    wsl=wsl.exe
  elif have_cmd wsl; then
    wsl=wsl
  fi
  if [[ -z "$wsl" ]]; then
    err 'SL_RUNTIME=wsl but wsl.exe was not found.'
    err 'This mode is for Windows hosts with WSL2. On Linux/macOS use process-compose or podman.'
    exit 1
  fi
  info 'delegating into WSL with SL_RUNTIME=process-compose'
  # Prefer wslpath when available so Windows drive paths resolve inside the distro.
  local unix_root="$REPO_ROOT"
  if have_cmd wslpath; then
    unix_root="$(wslpath -a "$REPO_ROOT" 2>/dev/null || true)"
  fi
  [[ -n "$unix_root" ]] || unix_root="$REPO_ROOT"
  exec "$wsl" -e bash -lc "cd \"$unix_root\" && SL_RUNTIME=process-compose ./scripts/runtime-up.sh"
}

invoke_apple() {
  if ! have_cmd container; then
    err 'SL_RUNTIME=apple|container but the Apple `container` CLI was not found.'
    err ''
    err 'Apple Container is macOS-only (OSS per-container VM). Elsewhere use:'
    err '  SL_RUNTIME=process-compose   # default'
    err '  SL_RUNTIME=podman            # OCI via Podman'
    err 'See crates/sl-daemon/README.md for container build/run examples.'
    exit 1
  fi

  local cf="${REPO_ROOT}/crates/sl-daemon/Containerfile"
  [[ -f "$cf" ]] || cf="${REPO_ROOT}/Containerfile"
  local image="${SL_CONTAINER_IMAGE:-sl-daemon:latest}"
  local data="${REPO_ROOT}/.sl-data"
  mkdir -p "${data}/sessions" "${data}/out"

  info "container build -t $image -f $cf ."
  container build -t "$image" -f "$cf" .
  info "container run --rm -v sessions/out -p 8080 $image"
  exec container run --rm \
    -v "${data}/sessions:/data/sessions" \
    -v "${data}/out:/data/out" \
    -p 8080:8080 \
    "$image" "$@"
}

show_engine_hints
runtime="$(resolve_runtime)"
info "SL_RUNTIME -> $runtime"

case "$runtime" in
  process-compose) invoke_process_compose "$@" ;;
  pheno) invoke_pheno "$@" ;;
  podman) invoke_podman "$@" ;;
  wsl) invoke_wsl "$@" ;;
  apple) invoke_apple "$@" ;;
esac
