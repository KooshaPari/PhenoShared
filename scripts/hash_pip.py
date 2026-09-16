#!/usr/bin/env python3
"""Generate per-workflow pip --require-hashes compatible requirements files.

Outputs:
- requirements-ci-base.txt       (pyyaml + pip; minimal CI deps)
- requirements-ci-test.txt       (base + pytest + coverage + numpy)
- requirements-ci-lint.txt       (base + ruff)
- requirements-ci-typecheck.txt  (base + mypy)
- requirements-ci-fuzz.txt       (pyyaml only, for kernels)
"""
import json
import sys
import urllib.request


def fetch_sha256(pkg: str, version: str) -> list[tuple[str, str]]:
    """Return list of (filename, sha256) tuples for all wheel+sdist files for pkg==version."""
    url = f"https://pypi.org/pypi/{pkg}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    files = data.get("urls", [])
    return [(f["filename"], f["digests"]["sha256"]) for f in files if "sha256" in f.get("digests", {})]


def format_reqs_lines(pkg: str, version: str, hashes: list[tuple[str, str]]) -> list[str]:
    """Format pkg==version + all wheel --hash entries (pip --require-hashes compatible)."""
    if not hashes:
        return [f"{pkg}=={version}"]
    wheels = [(fn, sha) for fn, sha in hashes if fn.endswith(".whl")]
    if not wheels:
        return [f"{pkg}=={version}", f"    --hash=sha256:{hashes[0][1]}"]
    lines = [f"{pkg}=={version}"]
    for _, sha in wheels:
        lines.append(f"    --hash=sha256:{sha}")
    return lines


def write_reqs(out: str, header: str, packages: list[tuple[str, str]]) -> None:
    lines = [f"# {header}", "# Generated via hash_pip.py -- do not edit by hand", "# Use: pip install --require-hashes -r <this-file>", ""]
    for pkg, ver in packages:
        print(f"  fetching {pkg}=={ver}...", file=sys.stderr)
        try:
            hashes = fetch_sha256(pkg, ver)
            lines.extend(format_reqs_lines(pkg, ver, hashes))
            lines.append("")
        except Exception as e:
            print(f"  ERROR {pkg}: {e}", file=sys.stderr)
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print(f"  wrote {out} ({len(packages)} packages)", file=sys.stderr)


def main() -> None:
    base = [
        ("pyyaml", "6.0.3"),    # Security patch (CVE-2024-...), stable
        ("pip", "26.2.1"),       # 6 CVEs fixed (path traversal, symlink, tar/zip, entry point)
    ]
    test_extra = [
        ("pytest", "9.1.1"),     # CVE-2025-71176 tmpdir handling fix
        ("coverage", "7.16.0"),  # Latest stable
        ("numpy", "2.5.2"),      # Latest stable, all OSV vulns fixed
    ]
    lint_extra = [
        ("ruff", "0.16.5"),      # Latest stable
    ]
    typecheck_extra = [
        ("mypy", "2.3.1"),       # Latest stable, all OSV vulns fixed
    ]

    write_reqs("requirements-ci-base.txt", "Base CI requirements (pyyaml + pip upgrade)", base)
    write_reqs("requirements-ci-test.txt", "Test runner requirements (base + pytest + coverage + numpy)", base + test_extra)
    write_reqs("requirements-ci-lint.txt", "Lint requirements (base + ruff)", base + lint_extra)
    write_reqs("requirements-ci-typecheck.txt", "Type-check requirements (base + mypy)", base + typecheck_extra)
    write_reqs("requirements-ci-fuzz.txt", "Fuzz/kernels requirements (pyyaml only)", [("pyyaml", "6.0.3")])


if __name__ == "__main__":
    main()
