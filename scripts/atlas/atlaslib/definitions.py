"""Constants, rule limits, and byte patterns for the codebase atlas.

Every rule encoded here comes from the repository's own `AGENTS.md`:
modules at or below 500 lines hard / 350 target, one file per concern with no
temporal filename suffixes, test variants handled by fixtures and markers
rather than filenames, and session artifacts confined to `docs/sessions/`.
"""

from __future__ import annotations

import re

# Rule limits from AGENTS.md: "Keep modules at or below 500 lines and target
# 350 lines; split by coherent responsibility."
LIMIT_TARGET = 350
LIMIT_HARD = 500

# Bytes of overlap carried across read chunks. Must exceed the longest pattern
# so matches spanning a chunk boundary are seen whole.
CARRY = 96
CHUNK = 1 << 20

CODE_EXT = frozenset(
    """rs py go ts tsx js jsx mjs mts cjs sh bash zsh fish ps1 c h cc cpp cxx
    hpp hh hxx cs java kt kts swift m mm zig mojo rb pl pm lua sql vue svelte
    astro proto tf hcl nix ex exs erl r jl nim""".split()
)
DOC_EXT = frozenset("md mdx rst adoc".split())
TEXT_EXT = CODE_EXT | DOC_EXT | frozenset("toml yml yaml json jsonl ini cfg txt lock csv".split())
BUILD_EXT = frozenset(
    "o rlib a so dylib dll exe wasm class pyc zip tar gz tgz bin db sqlite "
    "sqlite3 onnx pt pth safetensors gguf".split()
)

# Filename markers the repo's naming rule forbids. Versioning belongs in git
# history; test variants belong in fixtures and markers, not in file names.
BAD_NAME_TOKENS = (
    "_v2", "_v3", "_v4", "_new", "_old", "_final", "_temp", "_tmp", "_backup",
    "_bak", "_draft", "_complete", "_copy", "_orig", "_legacy", "_deprecated",
)
BAD_TEST_SUFFIX = ("_unit", "_fast", "_slow", "_integration", "_e2e", "_smoke", "_quick")
ARBITRARY_NUMBER = re.compile(r"(?:^|_)test(\d+)$|_\d+$")

# Canonical repo-level docs are allowed at the repository root by name.
ROOT_DOC_ALLOW = frozenset(
    """README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md
    LICENSE AGENTS.md CLAUDE.md ARCHITECTURE.md NOTICE ARCHIVED.md INDEX.md
    GLOSSARY.md GOVERNANCE.md COMPARISON.md ROADMAP.md DESIGN.md LOCALE.md
    TREE.txt""".split()
)
# Root-level docs matching these read as session/status debris, not canon.
STRAY_DOC_NOISE = re.compile(
    r"(PHASE|SENTRY_|_SUMMARY|_STATUS|STATUS-|_COMPLETE|_FINAL|VALIDATION_REPORT|"
    r"AUDIT_REPORT|_HANDOFF|_PROGRESS|START_HERE|PLAN\.md|TODO|NOTES)",
    re.IGNORECASE,
)

# A component's own README/CHANGELOG beside its manifest is normal, not stray.
STANDARD_DOC_NAMES = frozenset(
    """README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md
    LICENSE.md ARCHITECTURE.md AGENTS.md CLAUDE.md NOTES.md TODO.md
    DOMAIN_MODEL.md DESIGN.md LLD.md HLD.md ADR.md INDEX.md""".split()
)

ARCHIVE_TREES = (
    "_archived/", "archives/", "archive/", ".archive/", "historical/",
    "absorption/", "docs/absorbed-from/",
)
DEBRIS_RE = re.compile(r"(zz-archive|zz_archive|absorbed|/wt-|_archived|\.orig\b)")

# Byte patterns. Anything counted is defined here so the artifacts can cite it.
P_TEST_RS = re.compile(rb"#\[(?:[A-Za-z_][A-Za-z0-9_]*::)*test\]")
P_TEST_PY = re.compile(rb"[ \t]*(?:async[ \t]+)?def[ \t]+test_")
P_TEST_GO = re.compile(rb"func[ \t]+Test")
P_TEST_JS = re.compile(rb"[ \t]*(?:it|test)(?:\.(?:only|skip|each|todo))?[ \t]*\(")
P_MAIN_RS = re.compile(rb"(?:pub[ \t]+)?(?:async[ \t]+)?fn[ \t]+main[ \t]*\(")
P_MAIN_GO = re.compile(rb"func[ \t]+main[ \t]*\(")
P_CFG_OS = re.compile(rb"target_os[ \t]*=[ \t]*\"([^\"]+)\"")

# The literal redaction marker a scrubbing pass left in committed content.
# Built by concatenation so this module's own bytes do not trip the scan.
REDACTED = b"<" + b"REDACTED" + b">"

CODE_MAGICS = (
    b"\x7fELF",          # ELF
    b"\xcf\xfa\xed\xfe",  # Mach-O 64 LE
    b"\xca\xfe\xba\xbe",  # Mach-O universal
    b"\xfe\xed\xfa\xce",  # Mach-O 32 BE
    b"\xfe\xed\xfa\xcf",  # Mach-O 64 BE
    b"MZ",               # PE
)

OUT_DIR_REL = ("docs", "atlas", "codebase")
ARTIFACTS = ("INVENTORY.md", "FILES.md", "HYGIENE.md", "README.md")
