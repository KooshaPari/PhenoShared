#!/usr/bin/env zsh
# zsh pane-history hook for resume-all.
# Sourceed from ~/.zshrc (only when the user opts in via `session-snapshot pane-hook install`).
# Records the last command and recent stdout for each pane into a per-pane log file
# so that resume-all can replay history when reopening a session.
#
# Hard rules:
#  - NEVER break the user's shell. All errors go to .hook-errors.log, not stderr.
#  - NEVER log secrets. Strip ANSI, strip common API-key patterns, refuse if the prompt itself
#    mentions password|secret|token.
#  - Memory bounded. Each log file is rotation-truncated at 1 MiB.
#  - Opt-in. This file is no-op unless explicitly sourced.
# Guard against double-sourcing.
[[ -n "${RESUME_ALL_PANE_HOOK_LOADED:-}" ]] && return 0
typeset -g RESUME_ALL_PANE_HOOK_LOADED=1

# Required for ${var//(#b)(pattern)/repl} back-reference substitution.
setopt extendedglob 2>/dev/null
setopt no_err_exit 2>/dev/null
setopt no_pipe_fail 2>/dev/null
# Local options, restored at the end of the file.
setopt local_options 2>/dev/null

# --- tunable knobs (env-overridable) --------------------------------------
: ${RESUME_ALL_PANE_LOG_DIR:="$HOME/.local/share/resume-all/pane-logs"}
: ${RESUME_ALL_PANE_LOG_MAX_BYTES:=1048576}     # 1 MiB per log file
: ${RESUME_ALL_PANE_LOG_TAIL_BYTES:=262144}     # 256 KiB of stdout captured per command
: ${RESUME_ALL_PANE_LOG_MAX_ROWS:=50}          # cap rows appended per cmd
: ${RESUME_ALL_PANE_LOG_DISABLE_PATTERN:='(?i)(password|secret|token)[[:space:]]*[:=]'}
# Slice 7: RESUME_ALL_PANE_LOG_FAILSAFE — when set, the hook refuses to do
# any work if the log dir can't be created or written.  All precmd/preexec
# callbacks short-circuit on the _pane_log_ready flag below.  This prevents
# the hook from spamming the user's shell with errors when the FS is read-only
# (e.g. on a fresh host before $HOME/.local exists, or after a perms change).
: ${RESUME_ALL_PANE_LOG_FAILSAFE:=1}

# --- paths ----------------------------------------------------------------
typeset -g RESUME_ALL_PANE_LOG_DIR RESUME_ALL_PANE_LOG_ERROR_LOG
RESUME_ALL_PANE_LOG_ERROR_LOG="$RESUME_ALL_PANE_LOG_DIR/.hook-errors.log"

# Slice 7: probe-and-set.  _pane_log_ready=1 means logging is wired up;
# _pane_log_ready=0 means every writer will short-circuit.  Set once at
# source time so the precmd/preexec hot path doesn't redo the probe.
typeset -g _pane_log_ready=0
typeset -g _pane_log_fail_reason=""

if [[ -d "$RESUME_ALL_PANE_LOG_DIR" ]]; then
  if [[ -w "$RESUME_ALL_PANE_LOG_DIR" ]]; then
    _pane_log_ready=1
  else
    _pane_log_fail_reason="dir not writable"
  fi
else
  if mkdir -p "$RESUME_ALL_PANE_LOG_DIR" 2>/dev/null && [[ -w "$RESUME_ALL_PANE_LOG_DIR" ]]; then
    _pane_log_ready=1
  else
    _pane_log_fail_reason="mkdir failed"
  fi
fi

# Wrap every error path so the shell never sees a noisy fd.
# Slice 7: if the log dir failed its probe, don't even try to write the
# error log — the redirect itself would emit a stderr noise line.
_resume_all_hook_err() {
  # Args: msg
  (( _pane_log_ready )) || return 0
  {
    print -r -- "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $$: $1"
  } >> "$RESUME_ALL_PANE_LOG_ERROR_LOG" 2>/dev/null
  return 0
}

# Slice 7: warn-once at source time if the log dir is unwritable.  The
# FAILSAFE env var forces a single short message instead of a stderr warn;
# the user's shell is never killed or noisily interrupted.
if (( _pane_log_ready == 0 )); then
  if [[ "$RESUME_ALL_PANE_LOG_FAILSAFE" == "1" ]]; then
    # FAILSAFE: minimal output, no side effects.  Don't even try to write
    # the error log (which would itself fail on a read-only FS).
    print -- "resume-all pane-hook: hook loaded, logging unavailable (${_pane_log_fail_reason:-unknown})"
  else
    print -u2 -- "resume-all pane-hook: $RESUME_ALL_PANE_LOG_DIR ${_pane_log_fail_reason}; logging disabled"
    _resume_all_hook_err "log dir unavailable (${_pane_log_fail_reason}); hook disabled"
  fi
fi
# Strip ANSI escapes (CSI + a few stray forms), null bytes, and CR-only output.
_resume_all_strip_ansi() {
  # Use sed via a subshell so we never leak fd state to the parent shell.
  print -r -- "$1" | sed -E $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g; s/\x1b\\][^\x07]*\x07//g; s/\x1b[()=#].//g; s/\x1b//g; s/\r$//' 2>/dev/null
}

# Redact common secret patterns. Replace matched tokens with <redacted-secret>.
# Uses zsh's ${var//pattern/repl} with extended glob; patterns are anchored to known prefixes.
_resume_all_redact() {
  local line="$1"
  # OpenAI / Anthropic / GitHub / AWS / Slack / Google / PEM headers.
  # Each alternation is its own substitution so the regex engine stays simple.
  line="${line//(#b)(sk-[A-Za-z0-9_-]##)/<redacted-secret>}"
  line="${line//(#b)(sk_live_[A-Za-z0-9]##)/<redacted-secret>}"
  line="${line//(#b)(sk_test_[A-Za-z0-9]##)/<redacted-secret>}"
  line="${line//(#b)(ghp_[A-Za-z0-9]##)/<redacted-secret>}"
  line="${line//(#b)(gho_[A-Za-z0-9]##)/<redacted-secret>}"
  line="${line//(#b)(github_pat_[A-Za-z0-9_]##)/<redacted-secret>}"
  line="${line//(#b)(AKIA[0-9A-Z]##)/<redacted-secret>}"
  line="${line//(#b)(xoxb-[A-Za-z0-9-]##)/<redacted-secret>}"
  line="${line//(#b)(xoxp-[A-Za-z0-9-]##)/<redacted-secret>}"
  line="${line//(#b)(AIza[0-9A-Za-z_-]##)/<redacted-secret>}"
  line="${line//(#b)(-----BEGIN [A-Z ]#PRIVATE KEY-----)/<redacted-secret>}"
  print -r -- "$line"
}

# Decide whether the prompt itself asks for secrets; if so, refuse to write.
# Case-insensitive substring match against the prompt text.
_resume_all_prompt_is_secret() {
  local prompt="${1:-}"
  [[ -z "$prompt" ]] && return 1
  [[ "$prompt" == (#i)*password* ]] && return 0
  [[ "$prompt" == (#i)*secret* ]] && return 0
  [[ "$prompt" == (#i)*token* ]] && return 0
  return 1
}

# Compute the stable id for this pane. The pane is uniquely identified by its tty
# (T.TID — the device id of the controlling terminal). We hash just the tty so
# that resume-all can recompute the same file name from the snapshot row's tty
# when reopening a pane. The session_marker ($$ + start time) is intentionally
# excluded — it changes when the shell restarts, but the tty number is recycled
# in a way that lets the new pane see the previous pane's history.
_resume_all_pane_id() {
  {
    local tty_marker
    tty_marker="$(tty 2>/dev/null || print -r -- "notty")"
    # Strip the trailing newline so the hash matches the snapshot row's tty
    # (which is computed in Python without a trailing newline).
    tty_marker="${tty_marker//$'\n'/}"
    # Hash to a short, file-safe token. Use printf (no trailing newline) so the
    # hash is reproducible from outside the shell.
    printf "%s" "$tty_marker" \
      | shasum -a 256 \
      | awk '{print substr($1,1,24)}'
  } 2>/dev/null
}

# Periodic truncation: if the file exceeds the cap, keep the tail.
_resume_all_truncate() {
  local f="$1"
  local max="$RESUME_ALL_PANE_LOG_MAX_BYTES"
  [[ -f "$f" ]] || return 0
  local size
  size=$(($(stat -f %z "$f" 2>/dev/null || wc -c <"$f" 2>/dev/null || echo 0)))
  if (( size > max )); then
    # Keep the last `max` bytes; rewrite atomically.
    local tmp="${f}.trunc.$$"
    tail -c "$max" "$f" > "$tmp" 2>/dev/null && mv "$tmp" "$f" || _resume_all_hook_err "truncate failed"
  fi
}

# Append rows to the log with a single lock-ish guard using a per-pane .lock.
_resume_all_log_append() {
  local logfile="$1"
  shift
  local rows=("$@")
  [[ ${#rows[@]} -eq 0 ]] && return 0
  {
    local lock="${logfile}.lock"
    # mkdir is atomic on POSIX; bail if another tail is appending.
    if ! mkdir "$lock" 2>/dev/null; then
      # Try a few times quickly, then give up.
      local i=0
      while (( i < 5 )); do
        sleep 0.05
        mkdir "$lock" 2>/dev/null && break
        (( i++ ))
      done
      (( i >= 5 )) && { _resume_all_hook_err "lock contended, dropping ${#rows[@]} rows"; return 0; }
    fi
    {
      print -rl -- "${rows[@]}"
    } >> "$logfile" 2>/dev/null
    rmdir "$lock" 2>/dev/null
  } always {
    return 0
  }
  _resume_all_truncate "$logfile"
}

# Snapshot the pane's recent stdout via the terminal driver.
# Uses `print -p` only as a no-op probe; we do NOT try to buffer the terminal's
# scrollback (that would fight the user's terminal). Instead we capture the
# command's stdout/stderr by piping it through a tee at exec time.
# For this hook, we record: command text + exit code + duration + timestamp.
# Stdout buffering is provided by the *trace* mechanism when the user opts in
# further; for now, we keep the log minimal and safe.

# --- preexec hook: runs RIGHT BEFORE the command starts ------------------
_resume_all_pane_preexec() {
  # Slice 7: short-circuit if the log dir failed its probe.  This is the
  # hot path — if logging is unavailable, never even bother computing
  # the cmd-derived state.
  (( _pane_log_ready )) || return 0
  # Args: the command line.
  local cmd="$1"
  # Refuse to log if the prompt itself looks secret.
  local prompt_text="${ZSH_VERSION:+${PS1:-}}"
  if _resume_all_prompt_is_secret "$prompt_text"; then
    _resume_all_hook_err "preexec skipped: prompt contained secret-like text"
    return 0
  fi
  # Secrets in the command are redacted at *write* time in the precmd hook,
  # not refused outright here, so the user keeps a useful audit trail.
  typeset -g RESUME_ALL_PANE_LAST_CMD="$cmd"
  typeset -g RESUME_ALL_PANE_LAST_START="$(date +%s)"
  return 0
}

# --- precmd hook: runs RIGHT BEFORE the next prompt is shown -------------
_resume_all_pane_precmd() {
  # Slice 7: same short-circuit as preexec.
  (( _pane_log_ready )) || return 0
  # Record the last command's result.
  local last_status="$?"
  local cmd="${RESUME_ALL_PANE_LAST_CMD:-}"
  [[ -z "$cmd" ]] && return 0
  local start="${RESUME_ALL_PANE_LAST_START:-$(date +%s)}"
  local now duration
  now=$(date +%s)
  duration=$(( now - start ))
  typeset -g RESUME_ALL_PANE_LAST_CMD=""
  typeset -g RESUME_ALL_PANE_LAST_START=""

  # Refuse to log if the prompt itself looks secret.
  local prompt_text="${PS1:-}"
  if _resume_all_prompt_is_secret "$prompt_text"; then
    _resume_all_hook_err "precmd skipped: prompt contained secret-like text"
    return 0
  fi

  local pane_id
  pane_id="$(_resume_all_pane_id)"
  [[ -z "$pane_id" ]] && return 0
  local logfile="$RESUME_ALL_PANE_LOG_DIR/${pane_id}.log"
  # Make sure the dir exists.
  [[ -d "$RESUME_ALL_PANE_LOG_DIR" ]] || mkdir -p "$RESUME_ALL_PANE_LOG_DIR" 2>/dev/null

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # Strip ANSI + redact secrets from the command text before writing.
  local cmd_safe
  cmd_safe="$(_resume_all_strip_ansi "$cmd")"
  cmd_safe="$(_resume_all_redact "$cmd_safe")"
  # Trim to a single line to keep the log compact.
  local nl=$'\n'
  cmd_safe="${cmd_safe//$nl/ }"
  # Row format: ts | dur_s | exit | command
  local row="$ts | ${duration}s | exit=$last_status | $cmd_safe"
  # Clamp per-row length so a pathological paste doesn't blow up the log.
  if (( ${#row} > 2048 )); then
    row="${row[1,2048]}..."
  fi
  _resume_all_log_append "$logfile" "$row"
  return 0
}

# --- install hooks --------------------------------------------------------
# Test membership without using $array[(I)...] (which requires ZSH-specific subscript quirks).
_resume_all_array_contains() {
  # Args: array_name needle
  local -a arr
  local needle="$2"
  # shellcheck disable=SC2296
  eval 'arr=("${'"$1"'[@]}")'
  local el
  for el in "${arr[@]}"; do
    [[ "$el" == "$needle" ]] && return 0
  done
  return 1
}

if ! _resume_all_array_contains preexec_functions _resume_all_pane_preexec; then
  preexec_functions+=(_resume_all_pane_preexec)
fi
if ! _resume_all_array_contains precmd_functions _resume_all_pane_precmd; then
  precmd_functions+=(_resume_all_pane_precmd)
fi

# Make sure the data dir exists at source time.
[[ -d "$RESUME_ALL_PANE_LOG_DIR" ]] || mkdir -p "$RESUME_ALL_PANE_LOG_DIR" 2>/dev/null

return 0
