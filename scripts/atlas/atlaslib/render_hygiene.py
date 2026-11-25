"""Rendering for HYGIENE.md."""

from __future__ import annotations

import os
from collections import Counter

from .definitions import LIMIT_HARD, LIMIT_TARGET
from .render import header, table

CAP = 200


def _more(hidden: int, noun: str) -> str:
    return f"*…and {hidden} more {noun}.*" if hidden else ""


def render(revision: str, files: dict, h: dict, packages: dict) -> str:
    paths = sorted(files)
    total_redacted = sum(count for _, count in h["redacted"])
    archives = h["archive_trees"]
    out = header("PhenoShared hygiene report", revision, extra=[
        f"- Scope: {len(paths)} tracked files (`git ls-files`).",
        "",
        "The rules applied are the repository's own, from `AGENTS.md`: modules at "
        f"or below **{LIMIT_HARD} lines hard / {LIMIT_TARGET} target**; test files "
        "named `test_<concern>.rs` with variants handled by fixtures and markers "
        "instead of filename suffixes; session artifacts under `docs/sessions/` "
        "and canonical docs under `docs/`; generated targets, environments, model "
        "weights, and extension artifacts kept out of Git.",
        "",
        "Where the rule targets *source modules*, the report counts source files "
        "(regular, non-binary, source extension) first, because committed patches, "
        "binary blobs, generated JSON, and vendored dumps have meaningless newline "
        "counts and would otherwise inflate every headline number.",
        "",
        "## Headline",
        "",
        table(["finding", "count"], [
            ["SOURCE files over 500 lines (hard limit)", len(h["src_hard"])],
            ["SOURCE files over 350 lines (target)", len(h["src_target"])],
            ["all tracked files over 500 lines", len(h["over_hard"])],
            ["all tracked files over 350 lines", len(h["over_target"])],
            ["non-canonical test filenames", len(h["bad_test_names"])],
            ["`tests/` files that define tests but are not `test_*.rs`",
             len(h["noncanon_test_files"])],
            ["filenames with temporal suffixes", len(h["bad_names"])],
            ["markdown docs outside `docs/`", len(h["stray_docs_root"]) + len(h["stray_docs_nested"])],
            ["  — root-level, matching status/phase noise patterns", len(h["stray_docs_noise"])],
            ["  — standard component docs, set aside", len(h["component_docs"])],
            ["zero-byte tracked files", len(h["zero_byte"])],
            ["tracked symlinks", len(h["symlinks"])],
            ["files containing the literal `<REDACTED>` marker", len(h["redacted"])],
            ["total `<REDACTED>` occurrences", total_redacted],
            ["committed build artifacts / binaries", len(h["artifacts"])],
            ["files larger than 1 MiB", len(h["big_files"])],
            ["files in archive / absorption trees", sum(archives.values())],
            ["paths matching debris patterns", len(h["debris_paths"])],
            ["exact duplicate content groups", len(h["duplicate_groups"])],
            ["bytes reclaimable from exact duplicates", h["duplicate_wasted"]],
            ["text files missing a trailing newline", len(h["no_trailing_nl"])],
            ["workspace members with no `[package] description`", len(h["no_desc"])],
        ]),
        "",
        "---",
        "",
        f"## 1. File-size gate violations",
        "",
        f"**{len(h['src_hard'])} source files exceed the 500-line hard limit and "
        f"{len(h['src_target'])} exceed the 350-line target.** Counting every "
        f"tracked file regardless of type, {len(h['over_hard'])} exceed 500 and "
        f"{len(h['over_target'])} exceed 350 — the difference is committed patches, "
        "binary blobs, generated JSON, and vendored dumps to which the module rule "
        "does not meaningfully apply. Complete lists are in `FILES.md`; the 25 "
        "largest source files are shown here so this report stands alone.",
        "",
        table(["path", "LOC"], [[p, n] for p, n in h["src_target"][:25]]),
        "",
        "Source breaches by area (the actionable view):",
        "",
        table(["area", "source files over 350", "source files over 500"],
              [[area, over, hard] for area, over, hard in h["src_areas"][:25]]),
        "",
        f"## 2. Non-canonical test filenames ({len(h['bad_test_names'])})",
        "",
        "Test-variant suffixes (`_unit`, `_fast`, `_slow`, `_integration`, `_e2e`, "
        "`_smoke`, `_quick`) and arbitrary numbering. The repo rule is one file per "
        "concern, with variants selected by fixtures and markers.",
        "",
        _capped_table(["path", "violation"], h["bad_test_names"]),
        "",
        _more(max(0, len(h["bad_test_names"]) - CAP), "violations"),
        "",
        f"## 3. `tests/` files that define tests but are not `test_*.rs` "
        f"({len(h['noncanon_test_files'])})",
        "",
        "Rust integration tests must be named `test_<concern>.rs`. Helper modules "
        "inside `tests/` that declare no `#[test]` (for example `common/mod.rs`) "
        "are not test files and are deliberately excluded.",
        "",
        _capped_table(["path"], [(p,) for p in h["noncanon_test_files"]]),
        "",
        _more(max(0, len(h["noncanon_test_files"]) - CAP), "files"),
        "",
        f"## 4. Temporal filename suffixes ({len(h['bad_names'])})",
        "",
        "`_v2 _v3 _v4 _new _old _final _temp _tmp _backup _bak _draft _complete "
        "_copy _orig _legacy _deprecated`. Versioning belongs in git history.",
        "",
        _capped_table(["path", "violation"], h["bad_names"]),
        "",
        _more(max(0, len(h["bad_names"]) - CAP), "files"),
        "",
        f"## 5. Markdown docs outside `docs/` "
        f"({len(h['stray_docs_root']) + len(h['stray_docs_nested'])})",
        "",
        "Canonical repo docs are allowed at the root by name, and a component's "
        "own `README.md`/`CHANGELOG.md` beside its manifest is normal content. "
        f"Those standard component docs ({len(h['component_docs'])} files) are "
        "counted and then set aside. What remains is the finding: markdown living "
        "somewhere with no owning component and no `docs/` home.",
        "",
        f"**Root-level ({len(h['stray_docs_root'])}), of which "
        f"{len(h['stray_docs_noise'])} match status/phase noise patterns** "
        "(`PHASE*`, `SENTRY_*`, `*_SUMMARY`, `*_STATUS`, `*_COMPLETE`, "
        "`VALIDATION_REPORT`, `START_HERE`, `*_AUDIT_REPORT`, …):",
        "",
        _capped_table(["path"], [(p,) for p in h["stray_docs_noise"][:120]], cap=120),
        "",
        _more(max(0, len(h["stray_docs_noise"]) - 120), "noise-pattern docs"),
        "",
        f"**Nested outside `docs/`, non-standard names "
        f"({len(h['stray_docs_nested'])}) — top clusters:**",
        "",
        table(["directory", "docs"], [
            [d, c] for d, c in Counter(
                os.path.dirname(p) for p in h["stray_docs_nested"]).most_common(40)
        ]),
        "",
        "Worst single directories (most non-standard docs in one place):",
        "",
        _capped_table(["path"], [(p,) for p in h["stray_docs_nested"][:80]], cap=80),
        "",
        _more(max(0, len(h["stray_docs_nested"]) - 80), "docs"),
        "",
        f"<details><summary>Standard component docs set aside "
        f"({len(h['component_docs'])})</summary>",
        "",
        _capped_table(["path"], [(p,) for p in h["component_docs"]]),
        "",
        _more(max(0, len(h["component_docs"]) - CAP), "docs"),
        "",
        "</details>",
        "",
        f"## 6. Archive and absorption trees ({sum(archives.values())} files)",
        "",
        table(["tree", "files", "bytes"],
              [[t, c, h["archive_bytes"][t]]
               for t, c in sorted(archives.items(), key=lambda x: -x[1])]),
        "",
        f"A further {len(h['debris_paths'])} tracked paths match debris patterns "
        "(`zz-archive`, `absorbed`, `/wt-`, `_archived`, `.orig`):",
        "",
        table(["pattern", "paths"],
              [[k, c] for k, c in h["debris_buckets"].most_common()]),
        "",
        f"## 7. Zero-byte tracked files ({len(h['zero_byte'])})",
        "",
        "Empty tracked files are usually either legitimate `.gitkeep` "
        "placeholders or a sign that a generation step committed nothing.",
        "",
        table(["path"], [[p] for p in h["zero_byte"]]),
        "",
        "Clusters: " + (", ".join(
            f"`{d}` ×{c}" for d, c in Counter(
                os.path.dirname(p) for p in h["zero_byte"]).most_common()) or "(none)"),
        "",
        f"## 8. Literal `<REDACTED>` markers ({len(h['redacted'])} files, "
        f"{total_redacted} occurrences)",
        "",
        "A scrubbing pass replaced real values with the literal string "
        "`<REDACTED>` in committed content. This is broken output, not a "
        "placeholder convention: `FUNDING.yml` reads `github: <REDACTED>`, and "
        "`llms.txt` points at `<REDACTED>/phenotype-registry`, which is not a "
        "usable URL. Any consumer that reads these files gets a corrupted value.",
        "",
        "> Self-exclusion: the generator and its own output contain the marker as "
        "a search needle, so `scripts/atlas/**` and `docs/atlas/codebase/**` are "
        "excluded from this section by path.",
        "",
        "Worst offenders by occurrence count:",
        "",
        table(["path", "occurrences"], [[p, c] for p, c in h["redacted"][:40]]),
        "",
        "Clusters by directory:",
        "",
        table(["directory", "files"], [
            [d, c] for d, c in Counter(
                "/".join(p.split("/")[:2]) if p.count("/") >= 2 else
                ("(repo root)" if "/" not in p else p.split("/")[0])
                for p, _ in h["redacted"]).most_common(30)
        ]),
        "",
        f"## 9. Committed build artifacts and binaries ({len(h['artifacts'])})",
        "",
        "Tracked files carrying build-artifact extensions, living under a build "
        "cache path, or starting with ELF/Mach-O/PE magic bytes. The repo rule is "
        "to keep generated targets and extension artifacts out of Git.",
        "",
        table(["path", "reason", "bytes"],
              [[p, r, s] for p, r, s in h["artifacts"][:80]]),
        "",
        _more(max(0, len(h["artifacts"]) - 80), "artifacts"),
        "",
        f"## 10. Files larger than 1 MiB ({len(h['big_files'])})",
        "",
        table(["path", "bytes"], [[p, s] for p, s in h["big_files"]]),
        "",
        f"## 11. Exact duplicate content ({len(h['duplicate_groups'])} groups, "
        f"{h['duplicate_wasted']} reclaimable bytes)",
        "",
        "MD5 over full content, size-prefiltered. Top 40 groups by wasted bytes "
        "(size × (copies − 1)). Repeated identical trees are the strongest signal "
        "of absorbed debris that was copied rather than merged.",
        "",
        table(["bytes each", "copies", "wasted", "example paths"], [
            [s, len(g), s * (len(g) - 1),
             "<br>".join(g[:4]) + ("<br>…" if len(g) > 4 else "")]
            for g, s in h["duplicate_groups"][:40]
        ]),
        "",
        f"## 12. Missing trailing newline ({len(h['no_trailing_nl'])} text files)",
        "",
        _capped_table(["path"], [(p,) for p in h["no_trailing_nl"][:100]], cap=100),
        "",
        _more(max(0, len(h["no_trailing_nl"]) - 100), "files"),
        "",
        f"## 13. Workspace members without a `[package] description` "
        f"({len(h['no_desc'])})",
        "",
        "The inventory's `role` column falls back to the README, then to an "
        "inferred label prefixed `~`, for these.",
        "",
        table(["path", "package"],
              [[d or "(workspace root)", packages[d]["name"]] for d in h["no_desc"]]),
        "",
        "## 14. Tracked symlinks",
        "",
        "Tracked symlinks are counted separately from zero-byte files: they are "
        "not empty, they are indirections, and they can dangle on checkout.",
        "",
        table(["path"], [[p] for p in h["symlinks"]]),
        "",
        "## 15. Counting definitions and limits",
        "",
        "- LOC is a byte-level newline count. Generated and vendored files are "
        "included whenever they are tracked.",
        "- Test counts are pattern matches, not a compiler-verified test list.",
        "- Filename rules match case-insensitively on the stem, and are applied to "
        "source and test extensions only.",
        "- Duplicate detection is exact-content MD5 only, with a 16-byte floor; "
        "there is no near-duplicate or structural analysis.",
        "- `[package] description` is read with a minimal TOML table splitter, so "
        "unusual manifests (inline tables, dotted keys) may be missed.",
        "- Manifests are not evaluated: workspace inheritance, `build.rs` output, "
        "and feature-gated targets are all out of scope.",
        "- Findings are reported, never auto-fixed. Nothing in this repo was "
        "modified to produce this report.",
        "",
    ])
    return "\n".join(out)


def _capped_table(headers, rows, cap=CAP) -> str:
    return table(headers, rows[:cap])
