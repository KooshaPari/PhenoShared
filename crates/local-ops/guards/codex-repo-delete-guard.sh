#!/usr/bin/env bash
# Codex PreToolUse hook that blocks repository-deletion commands from JSON input.
set -euo pipefail

MAX_PAYLOAD_BYTES=65536
FAIL_CLOSED_MESSAGE="BLOCKED: unable to inspect pre-tool input safely."

fail_closed() {
  printf '%s\n' "$FAIL_CLOSED_MESSAGE" >&2
  exit 1
}

# Bound input before storing it in a shell variable. The guard must fail closed
# if its parser dependency or an inspectable JSON command is unavailable.
PAYLOAD="$(LC_ALL=C /usr/bin/head -c "$((MAX_PAYLOAD_BYTES + 1))" 2>/dev/null)"
[[ ${#PAYLOAD} -le $MAX_PAYLOAD_BYTES ]] || fail_closed
command -v python3 >/dev/null 2>&1 || fail_closed

# Parse JSON and shell-style tokens without evaluating either. Only known
# repository-deletion command forms receive deny decisions; parser failures
# fail closed with the fixed diagnostic above.
if ! DECISION="$(printf '%s' "$PAYLOAD" | python3 -c '
import json
import shlex
import sys

def tokenize(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    return [token.casefold() for token in lexer]

def command_segments(tokens):
    start = 0
    for index, token in enumerate(tokens):
        if token and all(character in ";&|" for character in token):
            if start < index:
                yield tokens[start:index]
            start = index + 1
    if start < len(tokens):
        yield tokens[start:]

def unwrap_command_prefix(segment):
    """Remove safe command-launch wrappers before applying the policy.

    Agents commonly prefix a command with env, sudo, or command.  These
    wrappers do not change the destructive operation, so the guard must not
    treat them as a bypass.  Only syntactically unambiguous forms are
    unwrapped; unknown wrapper options remain fail-safe (no allow decision).
    """
    index = 0
    while index < len(segment):
        wrapper = segment[index]
        if wrapper == "command":
            index += 1
            if index < len(segment) and segment[index] == "--":
                index += 1
            continue
        if wrapper == "sudo":
            index += 1
            while index < len(segment) and segment[index].startswith("-"):
                option = segment[index]
                index += 1
                if option in {"-u", "--user", "-g", "--group", "-h", "--host"} and index < len(segment):
                    index += 1
            continue
        if wrapper == "env":
            index += 1
            while index < len(segment):
                token = segment[index]
                if token == "--":
                    index += 1
                    break
                if token.startswith("-"):
                    index += 1
                    if token in {"-u", "--unset"} and index < len(segment):
                        index += 1
                    continue
                if "=" in token and token.split("=", 1)[0].replace("_", "a").isalnum():
                    index += 1
                    continue
                break
            continue
        break
    return segment[index:]

def delete_option(tokens):
    for index, token in enumerate(tokens):
        if token in {"-x", "--method", "--request"}:
            if index + 1 < len(tokens) and tokens[index + 1] == "delete":
                return True
        if token in {"-xdelete", "--method=delete", "--request=delete"}:
            return True
    return False

def inspect(command, depth=0):
    if depth > 4:
        raise ValueError("nested shell depth")
    tokens = tokenize(command)
    for raw_segment in command_segments(tokens):
        segment = unwrap_command_prefix(raw_segment)
        if segment[:3] == ["gh", "repo", "delete"]:
            return "repo-delete"
        if segment[:3] == ["thegent", "repo", "delete"]:
            return "thegent-repo-delete"
        if segment[:3] == ["forge", "repo", "delete"]:
            return "forge-repo-delete"
        if segment[:2] == ["gh", "api"] and delete_option(segment[2:]) and any("/repos/" in token or "repos/" in token for token in segment[2:]):
            return "gh-api-delete"
        if segment[:3] == ["gh", "api", "graphql"] and any("deleterepository" in token for token in segment[3:]):
            return "graphql-delete"
        if segment and segment[0] == "curl":
            arguments = segment[1:]
            if delete_option(arguments) and any("api.github.com/repos" in value or "github.com/api/repos" in value for value in arguments):
                return "curl-delete"
        if len(segment) >= 3 and segment[0] in {"sh", "bash", "zsh"} and segment[1] == "-c":
            nested = inspect(segment[2], depth + 1)
            if nested:
                return nested
    return ""

payload = json.load(sys.stdin)
command = payload.get("command") or payload.get("input") or ""
if not isinstance(command, str):
    raise ValueError("command is not text")
print(inspect(command))
' 2>/dev/null)"; then
  fail_closed
fi

case "$DECISION" in
  repo-delete)
    echo "BLOCKED: 'gh repo delete' is not permitted. Repository deletion is forbidden." >&2
    ;;
  gh-api-delete)
    echo "BLOCKED: 'gh api DELETE /repos/...' is not permitted. Repository deletion is forbidden." >&2
    ;;
  graphql-delete)
    echo "BLOCKED: 'gh api graphql deleteRepository' mutation is forbidden." >&2
    ;;
  curl-delete)
    echo "BLOCKED: 'curl DELETE' to GitHub repos API is forbidden." >&2
    ;;
  thegent-repo-delete)
    echo "BLOCKED: 'thegent repo delete' is not permitted. Repository deletion is forbidden." >&2
    ;;
  forge-repo-delete)
    echo "BLOCKED: 'forge repo delete' is not permitted. Repository deletion is forbidden." >&2
    ;;
  *)
    exit 0
    ;;
esac
exit 1
