#!/usr/bin/env python3
"""_make_tarball.py — helper used by scripts/sign_release.bat on Windows.

Builds a gzipped tarball of the current repo HEAD excluding caches,
build outputs, and the binary kernel artifact. Same logic as the
inline Python in scripts/sign_release.sh, just factored out so the
Windows .bat wrapper can call it without a bash interpreter.
"""
import sys
import os
import tarfile

OUT = sys.argv[1] if len(sys.argv) > 1 else "pheno-harness.tar.gz"

EXCLUDE_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "htmlcov", "dist",
    ".zig-cache", "zig-out", ".sandbox", ".coverage",
    "build", "target", "venv", "env",
}
# NOTE: eval/, state/, rust/, logs/ are NOT pruned wholesale —
# they contain code + config the consumer needs. Only sub-paths
# matching EXCLUDE_PATH_SUBSTRINGS below are skipped.
EXCLUDE_EXTS = {".pyc", ".tmp", ".egg-info", ".coverage", ".air"}
EXCLUDE_PATH_SUBSTRINGS = [
    "/.git/", "/.venv/", "/__pycache__/", "/.pytest_cache/",
    "/.ruff_cache/", "/.mypy_cache/", "/htmlcov/",
    "/dist/", "/eval/results/", "/logs/", "/.zig-cache/",
    "/zig-out/", "/rust/target/", "/state/wheels/",
    "/.sandbox/", "/.coverage", "/build/", "/target/",
    "qwen3_5_kernel",
    f"/{os.path.basename(OUT)}",
]

count = 0
size = 0
with tarfile.open(OUT, "w:gz") as tf:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            fp = os.path.join(root, f).replace("\\", "/").lstrip("./")
            ext = os.path.splitext(f)[1]
            if ext in EXCLUDE_EXTS:
                continue
            fp_norm = "/" + fp
            if any(sub in fp_norm for sub in EXCLUDE_PATH_SUBSTRINGS):
                continue
            try:
                tf.add(fp)
                count += 1
                size += os.path.getsize(fp)
            except OSError as e:
                print(f"skip {fp}: {e}", file=sys.stderr)

print(f"{count} files, {size // 1024} KB uncompressed")
print(f"tarball: {os.path.getsize(OUT) // 1024} KB ({OUT})")