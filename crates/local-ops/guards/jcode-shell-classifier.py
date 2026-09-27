#!/usr/bin/env python3
"""Extract guard-relevant shell commands without executing shell input.

Quoted arguments are data. Command/process substitutions and shell -c bodies
are inspected separately. This is classification, not a general shell sandbox.
"""
import json
import os
import re
import sys


SENSITIVE = {"rm", "mkfs", "dd", "shutdown", "reboot", "git", "gh", ":"}

# `gh` namespaces whose mutating subcommands are worth routing to approval.
GH_SUBCOMMANDS = {
    "repo", "secret", "variable", "api", "pr", "release", "workflow",
    "issue", "run", "cache", "gist", "label", "ruleset",
}

# Subcommands that change remote state (or pull remote artifacts to disk).
GH_WRITE_VERBS = {
    "create", "delete", "edit", "merge", "close", "reopen", "comment",
    "review", "upload", "download", "cancel", "rerun", "enable", "disable",
    "sync", "transfer", "archive", "fork", "set", "remove", "clear", "run",
    "unarchive", "rename", "lock", "unlock", "pin", "unpin", "ready",
    "approve", "reject", "publish", "import", "clone",
}


def lex(source):
    """Return words and operator boundaries, retaining quoted data as one word."""
    tokens, nested = [], []
    word, active, quote = "", False, ""
    i = 0
    while i < len(source):
        c = source[i]
        if quote == "'":
            if c == "'":
                quote = ""
            else:
                word += c
            i += 1
            continue
        if c == "\\" and i + 1 < len(source):
            word += source[i + 1]
            active = True
            i += 2
            continue
        if c == "`":
            end = i + 1
            while end < len(source):
                if source[end] == "\\":
                    end += 2
                elif source[end] == "`":
                    break
                else:
                    end += 1
            nested.append(source[i + 1:end])
            word += "SUBSTITUTION"
            active = True
            i = end + 1
            continue
        if source[i:i + 2] in {"$(", "<(", ">("}:
            end, level, subquote = i + 2, 1, ""
            while end < len(source):
                t = source[end]
                if t == "\\" and subquote != "'":
                    end += 2
                    continue
                if subquote:
                    if t == subquote:
                        subquote = ""
                elif t in "\"'":
                    subquote = t
                elif t == "(":
                    level += 1
                elif t == ")":
                    level -= 1
                    if not level:
                        break
                end += 1
            nested.append(source[i + 2:end])
            word += "SUBSTITUTION"
            active = True
            i = end + 1
            continue
        if quote == '"':
            if c == '"':
                quote = ""
            else:
                word += c
            i += 1
            continue
        if c in "\"'":
            quote, active = c, True
        elif c == "#" and not active:
            end = source.find("\n", i)
            i = len(source) if end == -1 else end
            continue
        elif c.isspace() or c in ";&|(){}":
            if active:
                tokens.append(word)
                word, active = "", False
            if c in ";&|(){}\n":
                tokens.append(None)
        else:
            word += c
            active = True
        i += 1
    if active:
        tokens.append(word)
    return tokens, nested


def classify(source, depth=0):
    if depth > 32:
        raise ValueError("shell nesting too deep")
    tokens, nested = lex(source)
    for body in nested:
        yield from classify(body, depth + 1)
    # Fork bomb: `:(){ :|:& };:`. Match the function definition *and* the
    # recursive call instead of counting bare colons. Heredoc bodies are not
    # parsed as shell here, so counting colons made every embedded Python or
    # JSON snippet containing `if x:` / `for y:` look like a fork bomb and
    # hard-blocked it with no approval path.
    if re.search(r":\s*\(\s*\)\s*\{", source) and re.search(r":\s*\|\s*:", source):
        yield ":(){ :"
    segment = []
    for token in tokens + [None]:
        if token is not None:
            segment.append(token)
            continue
        if segment:
            yield from inspect_segment(segment, depth)
        segment = []


def inspect_segment(words, depth):
    while words and (re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", words[0])
                     or words[0] in {"if", "then", "else", "elif", "do", "!"}):
        words = words[1:]
    if not words:
        return
    executable = os.path.basename(words[0])
    if executable in {"sudo", "env", "command", "exec", "nohup"}:
        rest = words[1:]
        while rest and (rest[0].startswith("-") or "=" in rest[0]):
            rest = rest[1:]
        yield from inspect_segment(rest, depth)
        return
    if executable in {"bash", "sh", "zsh", "dash"}:
        for i, arg in enumerate(words[1:], 1):
            if arg.startswith("-") and "c" in arg and i + 1 < len(words):
                yield from classify(words[i + 1], depth + 1)
                return
    if executable == "eval":
        yield from classify(" ".join(words[1:]), depth + 1)
        return
    if executable == "git" and (len(words) < 2 or words[1] not in {
        "push", "reset", "clean", "branch"
    }):
        return
    if executable == "gh":
        if len(words) < 2 or words[1] not in GH_SUBCOMMANDS:
            return
        # Mutating subcommands must reach the hook so it can route them to
        # approval. Read-only ones (list, view, status, clone, checks, ...)
        # are benign and dropped.
        if words[1] != "api" and words[2:3] and words[2] not in GH_WRITE_VERBS:
            return
    if executable == ":":
        return
    elif executable in SENSITIVE or executable.startswith("mkfs."):
        # Quoted prose must not become executable tokens or option substrings.
        args = [arg if not re.search(r"\s", arg) else "QUOTED_DATA" for arg in words[1:]]
        yield " ".join([executable, *args]) + " "


def main():
    payload = json.load(sys.stdin)
    command = payload.get("command", "")
    if isinstance(command, str):
        print("\n".join(classify(command)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, AttributeError):
        # Preserve the existing gate's fail-open behavior on parsing errors.
        pass
