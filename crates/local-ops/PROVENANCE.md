# Initial source capture

- Captured: 2026-08-15
- Inputs: six executable files from `~/bin` and two guard scripts from
  `~/.local/bin`.
- Admission check: no literal assignment to a key, secret, token, password,
  authorization, or bearer value was detected.
- Validation: Bash/Zsh syntax checks passed before this repository was
  published.
- Exclusions: package-managed client shims, product-owned source, broken
  legacy wrappers, binaries, backups, and all volatile runtime data.

## Absorption into phenotype-tooling

- Absorbed: 2026-09-14
- Source repo: [<REDACTED>/zz-merge-unk-local-ops](https://github.com/KooshaPari/zz-merge-unk-local-ops)
- Destination: `crates/local-ops/` in [<REDACTED>/PhenoTooling](https://github.com/KooshaPari/PhenoTooling)
- Source repo preserved as-is; no further development expected there.

## jcode approval-gate capture

- Captured: 2026-09-18
- Inputs: two files from `~/bin`, namely `jcode-tool-safety`, the `pre_tool`
  gate configured in `~/.jcode/config.toml`, and `jcode-shell-classifier.py`,
  the shell lexer the gate invokes from its own directory.
- Admission check: no literal assignment to a key, secret, token, password,
  authorization, or bearer value was detected.
- Validation: `bash -n` and `py_compile` pass.
  `tests/test_jcode_tool_safety.sh` drives the gate the way jcode does (tool
  name in `JCODE_HOOK_TOOL_NAME`, bare tool-input JSON on stdin) and reports
  71/71 across read-only, GitHub-write, history-rewrite, catastrophic, and
  scoped-delete cases. It removes every inbox record it creates.
- Active path: `~/bin`. This capture is the source of record only and does not
  change the active command path.
- Defects found and fixed while capturing:
  - `gh api` writes were recognised only in the literal
    `-X POST|PUT|PATCH|DELETE` spelling. `--method PATCH`, `-XPATCH`,
    `--method=DELETE`, and the implicit-POST body flags (`-f`, `--field`, `-F`,
    `--raw-field`, `--input`) all bypassed approval.
  - Mutating subcommands outside `gh api` (`gh pr merge`, `gh release create`,
    `gh workflow run`, `gh repo archive`, `gh cache delete`, and others) were
    never gated, because the classifier dropped them before the gate saw them.
  - Read-only `gh secret list` and `gh variable list` were routed to approval.
  - `git push --follow-tags` matched the short force-flag test.
  - `rm -rf /etc` and `rm -rf /usr` were not hard-blocked, because the pattern
    required a non-letter character after `/`.
  - The classifier treated any three bare `:` tokens as a fork bomb, so an
    embedded Python or JSON heredoc containing `if x:` or `for y:` was
    hard-blocked with no approval path available.
  - Block mode carried a second, hand-maintained copy of the detection patterns
    that had already drifted from the elicitate path. Both modes now share one
    list through a `gate()` wrapper.
