#!/bin/bash
# bead-ctl: Append-only bead entry writer for the phenotype fleet
# Usage:
#   ./bead-ctl.sh claim <target> "<text>"     # claim work on a target
#   ./bead-ctl.sh complete <target> "<text>"  # mark work complete
#   ./bead-ctl.sh warn <target> "<text>"      # viewing/audit warning
#   ./bead-ctl.sh ctl <target> "<text>"       # control/operational entry
#   ./bead-ctl.sh reorg <target> "<text>"     # cleanup/reorganize another agent's work
#   ./bead-ctl.sh dedup                      # check for duplicates
#   ./bead-ctl.sh stats                      # show stats
#   ./bead-ctl.sh help                       # show this help
#
# Optional structured evidence is supplied through environment variables so
# existing three-argument calls stay valid:
#   BEAD_FR_ID=FR-6 BEAD_SESSION=session-42 BEAD_OUTCOME='installed smoke passed' \
#     ./bead-ctl.sh complete repo/target "evidence text"
#
# Each entry gets:
#   - bead_id (8-char hash)
#   - agent_id (ephemeral 8-char hash from hostname+pidof+timestamp)
#   - dedup_hash (8-char hash of target+kind+text)
#   - timestamp (UTC ISO 8601)

set -e

BEADS_FILE="/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl"
BEADS_LOCK="/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-dag/.beads.lock"

# Path to the pheno-harness repo root, used by the dual-write block to
# import the AgilePlus adapter. Override with PHENO_HARNESS_ROOT env
# var if the layout differs (e.g. in airlock-only environments).
PHENO_HARNESS_ROOT="${PHENO_HARNESS_ROOT:-/Users/kooshapari/CodeProjects/Phenotype/repos/pheno-harness}"

# Compute ephemeral agent identity (deterministic across calls in same session)
HOSTNAME=$(hostname -s 2>/dev/null || echo "unknown")
SESSION_TS=$(date +%s)
AGENT_ID="agent-$(echo "$HOSTNAME-$SESSION_TS" | shasum -a 256 | cut -c1-8)"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

hash8() {
  echo "$1" | shasum -a 256 | cut -c1-8
}

show_help() {
  cat << 'EOF'
bead-ctl — Append-only bead entry writer for phenotype fleet

Usage:
  bead-ctl [--backend=<jsonl|agileplus>] <subcommand> [args]

Global flags (must appear before the subcommand):
  --backend=jsonl       Legacy JSONL-only mode (default).
  --backend=agileplus   JSONL + AgilePlus dual-write (fail-soft).

Subcommands:
  bead-ctl claim <target> "<text>"     # claim work on target
  bead-ctl complete <target> "<text>"  # mark work complete
  bead-ctl warn <target> "<text>"      # viewing/audit warning
  bead-ctl ctl <target> "<text>"       # control/operational entry
  bead-ctl reorg <target> "<text>"     # cleanup/reorganize
  bead-ctl goal <target> "<text>"      # long-lived objective (slow burn)
  bead-ctl intent <target> "<text>"    # near-term session intent
  bead-ctl prompt <target> "<text>"    # user/agent prompt that motivated work
  bead-ctl migrate --from-jsonl ...    # one-time migration to AgilePlus
  bead-ctl dedup                       # check for duplicates
  bead-ctl stats                       # show stats
  bead-ctl agent                       # print current agent identity

Each bead is JSON on a single line: {id, ts, agent, kind, target, text, hash}
Dedup: hash = sha256(target + kind + text)[:8]

Structured metadata (all optional):
  BEAD_FR_ID, BEAD_SESSION, BEAD_AGENT_SESSION_ID, BEAD_PROMPT_TEXT,
  BEAD_INTENT_SYNTHESIS, BEAD_GOAL_ID, BEAD_PROMPT_INTENT_REF,
  BEAD_USER_OUTCOME, BEAD_OUTCOME, BEAD_OWNER, BEAD_SEVERITY,
  BEAD_STATE, BEAD_ACTION, BEAD_CLEARANCE_EVIDENCE
The JSONL ledger preserves these fields. AgilePlus dual-write remains
best-effort and may not support every metadata field.

Bead kinds:
  claim / complete / reorg  → kanban work column (claim → complete)
  warn                      → eyes/audit findings, blockers
  ctl                       → operational snapshots, ownership claims
  goal / intent / prompt    → PM-lite layer: why-work, what-now, how-got-here
EOF
}

ensure_beads_file() {
  mkdir -p "$(dirname "$BEADS_FILE")"
  touch "$BEADS_FILE"
}

add_bead() {
  local kind=$1
  local target=$2
  local text=$3

  ensure_beads_file

  # Include explicit metadata in the dedup identity. Two otherwise-identical
  # records with different release evidence are not the same record.
  local metadata_signature
  metadata_signature="${BEAD_FR_ID:-}|${BEAD_SESSION:-}|${BEAD_AGENT_SESSION_ID:-}|${BEAD_PROMPT_TEXT:-}|${BEAD_INTENT_SYNTHESIS:-}|${BEAD_GOAL_ID:-}|${BEAD_PROMPT_INTENT_REF:-}|${BEAD_USER_OUTCOME:-}|${BEAD_OUTCOME:-}|${BEAD_OWNER:-}|${BEAD_SEVERITY:-}|${BEAD_STATE:-}|${BEAD_ACTION:-}|${BEAD_CLEARANCE_EVIDENCE:-}"

  # Compute dedup hash
  local dedup_hash
  dedup_hash=$(hash8 "${target}|${kind}|${text}|${metadata_signature}")

  # Check for duplicates (handles both with/without space after colon)
  if grep -qE "\"hash\": *\"${dedup_hash}\"" "$BEADS_FILE" 2>/dev/null; then
    echo "DUPLICATE: bead with hash ${dedup_hash} already exists for ${target}/${kind}"
    return 1
  fi

  # Compute bead id
  local bead_id
  bead_id=$(hash8 "${AGENT_ID}|${TS}|${dedup_hash}")

  # Build JSON entry
  local entry
  entry=$(python3 -c "
import json, os, sys
entry = {
    'id': '${bead_id}',
    'ts': '${TS}',
    'agent': '${AGENT_ID}',
    'kind': '${kind}',
    'target': sys.argv[1],
    'text': sys.argv[2],
    'hash': '${dedup_hash}',
    'host': '${HOSTNAME}'
}
metadata = {
    'frId': os.environ.get('BEAD_FR_ID'),
    'session': os.environ.get('BEAD_SESSION'),
    'agentSessionId': os.environ.get('BEAD_AGENT_SESSION_ID'),
    'promptText': os.environ.get('BEAD_PROMPT_TEXT'),
    'intentSynthesis': os.environ.get('BEAD_INTENT_SYNTHESIS'),
    'goalId': os.environ.get('BEAD_GOAL_ID'),
    'promptIntentRef': os.environ.get('BEAD_PROMPT_INTENT_REF'),
    'userOutcome': os.environ.get('BEAD_USER_OUTCOME'),
    'outcome': os.environ.get('BEAD_OUTCOME'),
    'owner': os.environ.get('BEAD_OWNER'),
    'severity': os.environ.get('BEAD_SEVERITY'),
    'state': os.environ.get('BEAD_STATE'),
    'requiredAction': os.environ.get('BEAD_ACTION'),
    'clearanceEvidence': os.environ.get('BEAD_CLEARANCE_EVIDENCE'),
}
entry.update({key: value for key, value in metadata.items() if value})
print(json.dumps(entry))
" "$target" "$text")

  # Append atomically (write to temp + rename)
  local tmp_file="${BEADS_FILE}.tmp.$$"
  echo "$entry" >> "$BEADS_FILE"
  rm -f "$tmp_file"

  # Dual-write to AgilePlus when configured (task 28). Fail-soft: any
  # error is logged but does NOT fail the bead-ctl call. The JSONL
  # write above is the canonical source of truth.
  _dual_write_to_agileplus "$kind" "$target" "$text" "$bead_id" "$dedup_hash" || \
    echo "  [dual-write] AgilePlus append failed (logged); JSONL is the source of truth."

  # Audit-log mirror (task 35). Appends the same entry to
  # ~/.agileplus/audit.jsonl so operators have a dedicated log
  # covering all dual-write attempts. Fail-soft.
  _audit_log_append "$entry" || \
    echo "  [audit-log] append failed (logged); JSONL is the source of truth."

  echo "BEAD: ${bead_id} | ${kind} | ${target} | hash=${dedup_hash}"
  echo "  Agent: ${AGENT_ID}"
  echo "  Text: ${text}"
}

# _audit_log_append — mirror the bead entry to ~/.agileplus/audit.jsonl.
#
# Task 35 ac_v1. Every successful add_bead() call writes its full
# JSON entry (same shape as the JSONL line) to the audit log. The
# audit log is intentionally a separate file from the canonical
# beads.jsonl — operators tail it for "what was written" without
# touching the canonical store.
#
# Honors AGILEPLUS_AUDIT_LOG env var (defaults to
# ~/.agileplus/audit.jsonl). Set to /dev/null to disable.
_audit_log_append() {
  local entry="$1"
  local audit_log="${AGILEPLUS_AUDIT_LOG:-$HOME/.agileplus/audit.jsonl}"
  if [ "$audit_log" = "/dev/null" ]; then
    return 0
  fi
  mkdir -p "$(dirname "$audit_log")" 2>/dev/null || return 1
  printf '%s\n' "$entry" >> "$audit_log" 2>/dev/null || {
    echo "  [audit-log] write to $audit_log failed" >&2
    return 1
  }
}

# _dual_write_to_agileplus — append the bead to AgilePlus via the
# Python adapter (beads/agileplus_adapter/agileplus_adapter.py).
#
# Returns 0 on success OR when dual-write is disabled.
# Returns non-zero only when dual-write is enabled but the AgilePlus
# append failed. The caller treats this as advisory (logs + continues).
#
# Honor environment overrides:
#   BEADS_DUAL_WRITE=0       → force-disable (overrides config file)
#   BEADS_DUAL_WRITE=1       → force-enable  (overrides config file)
#   AGILEPLUS_HOST/PORT      → adapter URL
#   AGILEPLUS_API_TOKEN      → bearer token
#   AGILEPLUS_CONFIG         → path to config.json (default ~/.agileplus/config.json)
_dual_write_to_agileplus() {
  local kind="$1"
  local target="$2"
  local text="$3"
  local bead_id="$4"
  local dedup_hash="$5"

  # Resolve the effective enabled state.
  local enabled
  if [ -n "${BEADS_DUAL_WRITE:-}" ]; then
    enabled="${BEADS_DUAL_WRITE}"
  else
    enabled=$(PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, is_enabled
try:
    cfg = load_config(os.environ.get('AGILEPLUS_CONFIG'))
except Exception:
    cfg = {}
print('1' if is_enabled(cfg) else '0')
" 2>/dev/null) || enabled=0
  fi

  if [ "$enabled" != "1" ]; then
    return 0  # dual-write disabled → silent no-op
  fi

  # Attempt the AgilePlus append. Fail-soft: errors are caught and
  # logged, never propagated.
  PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, resolve_token
from beads.agileplus_adapter.agileplus_adapter import AgilePlusBeadStore, BeadStoreError

cfg = load_config(os.environ.get('AGILEPLUS_CONFIG'))
cfg['api_token'] = resolve_token(cfg)
try:
    store = AgilePlusBeadStore(
        host=cfg.get('host'),
        port=cfg.get('port'),
        base_url=cfg.get('base_url'),
        token=cfg.get('api_token'),
        timeout=cfg.get('timeout'),
        work_package_id=cfg.get('work_package_id'),
    )
    bead = AgilePlusBeadStore  # noqa
    from beads.agileplus_adapter.agileplus_adapter import Bead
    bead = Bead(
        id='$bead_id',
        ts='$TS',
        agent='$AGENT_ID',
        kind='$kind',
        target='$target',
        text='''$text''',
        hash='$dedup_hash',
        host='$HOSTNAME',
    )
    returned_id = store.append(bead)
    print(f'  [dual-write] AgilePlus ok: id={returned_id}')
except BeadStoreError as exc:
    print(f'  [dual-write] AgilePlus error: {exc}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'  [dual-write] unexpected error: {exc}', file=sys.stderr)
    sys.exit(1)
" || return 1
  return 0
}

# _cmd_migrate — one-time migration script that pushes existing JSONL
# beads to AgilePlus. Idempotent (uses dedup_check to skip existing
# beads). Run as:
#
#   bead-ctl migrate --from-jsonl [--dry-run] [--limit N] [--yes]
#
# Flags:
#   --from-jsonl    (required) source is the legacy JSONL file.
#   --dry-run       Report what would happen; make no API calls.
#   --limit N       Process at most N beads (default: all).
#   --yes           Skip the interactive confirmation prompt.
#
# Exit codes:
#   0  all beads migrated (or skipped because already present)
#   1  one or more beads failed to migrate (logged per-bead)
#   2  invalid arguments / missing prerequisites
_cmd_migrate() {
  local dry_run=0
  local limit=0
  local yes=0
  local from_jsonl=0

  while [ $# -gt 0 ]; do
    case "$1" in
      --from-jsonl) from_jsonl=1 ;;
      --dry-run) dry_run=1 ;;
      --limit) limit="$2"; shift ;;
      --yes) yes=1 ;;
      *) echo "Unknown migrate flag: $1" >&2; exit 2 ;;
    esac
    shift
  done

  if [ "$from_jsonl" != "1" ]; then
    echo "ERROR: --from-jsonl is required (other sources not yet supported)" >&2
    exit 2
  fi
  if [ ! -f "$BEADS_FILE" ]; then
    echo "No beads file at $BEADS_FILE; nothing to migrate."
    exit 0
  fi

  # Confirm (unless --yes).
  if [ "$yes" != "1" ] && [ "$dry_run" != "1" ]; then
    echo "Migrate beads from $BEADS_FILE → AgilePlus?"
    echo "  enabled: $(PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import os, sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, is_enabled
print('yes' if is_enabled(load_config(os.environ.get('AGILEPLUS_CONFIG'))) else 'no')
" 2>/dev/null || echo 'unknown')"
    echo "  limit:   ${limit:-all}"
    echo -n "Proceed? [y/N] "
    read -r answer
    case "$answer" in
      y|Y|yes|YES) ;;
      *) echo "Aborted."; exit 0 ;;
    esac
  fi

  PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import json
import os
import sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, resolve_token
from beads.agileplus_adapter.agileplus_adapter import (
    AgilePlusBeadStore, Bead, BeadStoreError,
)

cfg = load_config(os.environ.get('AGILEPLUS_CONFIG'))
cfg['api_token'] = resolve_token(cfg)
store = AgilePlusBeadStore(
    host=cfg.get('host'),
    port=cfg.get('port'),
    base_url=cfg.get('base_url'),
    token=cfg.get('api_token'),
    timeout=cfg.get('timeout'),
    work_package_id=cfg.get('work_package_id'),
)

dry_run = ${dry_run}
limit = ${limit}

imported = 0
skipped = 0
failed = 0
total = 0
with open('$BEADS_FILE') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        if limit and total > limit:
            break
        bead = Bead(
            id=entry.get('id', ''),
            ts=entry.get('ts', ''),
            agent=entry.get('agent', ''),
            kind=entry.get('kind', ''),
            target=entry.get('target', ''),
            text=entry.get('text', ''),
            hash=entry.get('hash', ''),
            host=entry.get('host', ''),
        )
        if dry_run:
            print(f'  [dry-run] would import {bead.id} {bead.kind} {bead.target}')
            continue
        try:
            if store.dedup_check(bead):
                skipped += 1
                continue
            new_id = store.append(bead)
            imported += 1
            print(f'  imported {bead.id} → AgilePlus id={new_id}')
        except BeadStoreError as exc:
            failed += 1
            print(f'  FAILED {bead.id}: {exc}', file=sys.stderr)

print(f'\\nMigration summary: total={total} imported={imported} skipped={skipped} failed={failed}')
sys.exit(1 if failed > 0 else 0)
"
}

cmd="${1:-help}"

# Pre-scan for --backend=<jsonl|agileplus> global flag (must appear
# before the subcommand). Sets BEADS_BACKEND for the dual-write block.
backend="${BEADS_BACKEND:-}"
while [ "${cmd:0:9}" = "--backend" ] || [ "$cmd" = "--backend" ]; do
  case "$cmd" in
    --backend=*) backend="${cmd#--backend=}" ;;
    --backend)
      # --backend <value> form: consume next arg.
      backend="${1:-}"
      shift || true
      cmd="${1:-help}"
      continue
      ;;
  esac
  shift || true
  cmd="${1:-help}"
done

# Resolve backend: explicit > env > default 'jsonl'.
# 'jsonl' = legacy JSONL-only; 'agileplus' = JSONL + AgilePlus dual-write.
if [ -z "$backend" ]; then
  backend="${BEADS_BACKEND:-jsonl}"
fi
case "$backend" in
  jsonl|agileplus) ;;
  *) echo "ERROR: invalid backend '$backend' (expected jsonl or agileplus)" >&2; exit 2 ;;
esac
# Backward compat: BEADS_DUAL_WRITE is the legacy name; map to backend.
if [ "$backend" = "agileplus" ]; then
  BEADS_DUAL_WRITE="${BEADS_DUAL_WRITE:-1}"
fi
export BEADS_BACKEND="$backend"

shift || true

case "$cmd" in
  claim|complete|warn|ctl|reorg|goal|intent|prompt)
    target="${1:-}"
    text="${2:-}"
    if [ -z "$target" ] || [ -z "$text" ]; then
      echo "ERROR: target and text required for ${cmd}"
      echo "Usage: bead-ctl ${cmd} <target> \"<text>\""
      exit 1
    fi
    add_bead "$cmd" "$target" "$text"
    ;;
  agent)
    echo "$AGENT_ID"
    ;;
  migrate)
    # Migrate legacy JSONL beads to AgilePlus. Idempotent — uses
    # dedup_check() to skip beads whose hash already exists.
    # Note: do NOT shift — _cmd_migrate needs the full "$@" to parse
    # its flags.
    _cmd_migrate "$@"
    ;;
  dedup)
    echo "Checking duplicates..."
    if [ -f "$BEADS_FILE" ]; then
      dupes=$(python3 -c "
import json, sys
from collections import Counter
hashes = Counter()
with open('${BEADS_FILE}') as f:
    for line in f:
        try:
            entry = json.loads(line)
            hashes[entry.get('hash', '')] += 1
        except: pass
for h, n in hashes.items():
    if n > 1:
        print(f'  {h}: {n}x')
if not any(n > 1 for n in hashes.values()):
    print('  No duplicates found')
" 2>&1)
      echo "$dupes"
    else
      echo "  No beads file yet"
    fi
    ;;
  stats)
    echo "Bead stats:"
    if [ ! -f "$BEADS_FILE" ]; then
      echo "  No beads yet"
      exit 0
    fi
    python3 -c "
import json
from collections import Counter
kinds = Counter()
agents = Counter()
targets = Counter()
n = 0
with open('${BEADS_FILE}') as f:
    for line in f:
        try:
            entry = json.loads(line)
            n += 1
            kinds[entry.get('kind','?')] += 1
            agents[entry.get('agent','?')] += 1
            targets[entry.get('target','?')] += 1
        except: pass
print(f'  Total beads: {n}')
print(f'  By kind:    {dict(kinds)}')
print(f'  By agent:   {dict(agents)}')
print(f'  Top targets: {targets.most_common(5)}')
"
    ;;
  help|--help|-h|"")
    show_help
    ;;
  *)
    echo "Unknown command: $cmd"
    show_help
    exit 1
    ;;
esac
