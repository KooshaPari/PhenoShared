#!/usr/bin/env python3
"""Generate per-workflow pip --require-hashes compatible requirements files.

Run from the repository root; the five files are written into the current
working directory.

Outputs:
- requirements-ci-base.txt       (pyyaml + pip; minimal CI deps)
- requirements-ci-test.txt       (base + pytest + coverage + numpy)
- requirements-ci-lint.txt       (base + ruff)
- requirements-ci-typecheck.txt  (base + mypy)
- requirements-ci-fuzz.txt       (pyyaml only, for kernels)

Two rules make a requirements file usable under ``pip install
--require-hashes``; both are enforced below, and ``verify_reqs_text`` re-checks
the emitted text before it is written.

1. Every requirement must be attached to its hashes by a backslash
   continuation. Each requirement is emitted in pip-compile form, one hash per
   line::

       pkg==1.2.3 \\
           --hash=sha256:... \\
           --hash=sha256:...

   The requirement line and every continuation except the last carry a
   trailing backslash. pip only honours an indented ``--hash`` that is
   attached to a requirement by a continuation: an indented ``--hash`` under a
   requirement line that does not end in a backslash is parsed as a standalone
   line, dropped with "has --hash but no requirement, and will be ignored", and
   then ``--require-hashes`` rejects the whole file because hashes are missing.

2. Every requirement in the resolved dependency set must be pinned with ``==``
   and must carry a hash, not only the top-level tools. pip rejects the whole
   file with "In --require-hashes mode, all requirements must have their
   versions pinned with ==" as soon as one transitive dependency is unpinned.
   The package lists in ``main`` therefore carry the complete closure.

Each file pins every requirement to the exact sha256 of every published
distribution file (wheels and sdist) for that version, so
``pip install --require-hashes -r <this-file>`` succeeds on any platform that
has a matching wheel, and can fall back to a source build whose hash is also
listed.
"""
import json
import sys
import urllib.request


def fetch_sha256(pkg: str, version: str) -> list[tuple[str, str]]:
    """Return (filename, sha256) for every distribution file of pkg==version.

    Sorted by filename so that regenerating a requirements file is byte-for-byte
    stable even if PyPI changes the order it lists files in.
    """
    url = f"https://pypi.org/pypi/{pkg}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    files = data.get("urls", [])
    entries = [
        (f["filename"], f["digests"]["sha256"])
        for f in files
        if f.get("digests", {}).get("sha256")
    ]
    return sorted(entries)


def format_reqs_lines(pkg: str, version: str, hashes: list[tuple[str, str]]) -> list[str]:
    """Format pkg==version plus every hash as a pip-compile requirement block.

    The requirement line ends with a backslash, every hash line but the last
    ends with a backslash, and the last hash line does not. An indented
    ``--hash`` that is not attached by a continuation is ignored by pip.
    """
    if not hashes:
        raise ValueError(
            f"{pkg}=={version} has no published distribution files, "
            "so it cannot be pinned with --hash"
        )
    lines = [f"{pkg}=={version} \\"]
    last = len(hashes) - 1
    for index, (_, sha) in enumerate(hashes):
        continuation = "" if index == last else " \\"
        lines.append(f"    --hash=sha256:{sha}{continuation}")
    return lines


def verify_reqs_text(text: str, path: str) -> None:
    """Fail loudly when the emitted text is not valid ``--require-hashes`` input.

    Checks the two rules pip enforces on a requirements file: every indented
    ``--hash`` line must be attached to a requirement by a backslash
    continuation, and every requirement must carry at least one hash.
    """
    problems: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line != line.lstrip():
            problems.append(
                f"{path}:{index + 1}: indented line with no attached requirement: {line!r}"
            )
            index += 1
            continue
        if not line.endswith("\\"):
            problems.append(
                f"{path}:{index + 1}: requirement has no hash continuation: {line!r}"
            )
            index += 1
            continue
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].startswith("    --hash=sha256:"):
            cursor += 1
        if cursor == index + 1:
            problems.append(f"{path}:{index + 1}: requirement has no --hash: {line!r}")
        elif lines[cursor - 1].endswith("\\"):
            problems.append(
                f"{path}:{cursor}: final --hash line must not end with a backslash"
            )
        index = cursor
    if problems:
        raise SystemExit(
            "hash_pip.py: generated file is not --require-hashes compatible:\n  "
            + "\n  ".join(problems)
        )


def write_reqs(out: str, header: str, packages: list[tuple[str, str]]) -> None:
    blocks: list[tuple[str, str]] = []
    for pkg, ver in packages:
        print(f"  fetching {pkg}=={ver}...", file=sys.stderr)
        try:
            hashes = fetch_sha256(pkg, ver)
        except Exception as e:
            raise SystemExit(f"  ERROR {pkg}=={ver}: {e}") from e
        blocks.append((pkg.lower(), "\n".join(format_reqs_lines(pkg, ver, hashes))))
    text = (
        f"# {header}\n"
        "# Generated via hash_pip.py -- do not edit by hand\n"
        "# Use: pip install --require-hashes -r <this-file>\n"
        "# Hashes use the pip-compile backslash-continuation form; do not strip the backslashes.\n"
        "\n"
        + "\n\n".join(block for _, block in sorted(blocks))
        + "\n"
    )
    verify_reqs_text(text, out)
    with open(out, "w") as f:
        f.write(text)
    print(f"  wrote {out} ({len(packages)} packages)", file=sys.stderr)


def main() -> None:
    # The package lists below are the complete dependency closure of each file,
    # not only its top-level tools: pip --require-hashes rejects a file unless
    # every requirement in the resolved set is pinned with == and carries a
    # hash. The closure was resolved for Python 3.12 on Linux x86_64/aarch64
    # and macOS arm64/x86_64 (the platforms this repository's CI runs on).
    # Re-derive it after changing a top-level pin with:
    #
    #   python3 -m pip install --dry-run --ignore-installed --report r.json \
    #     --only-binary=:all: --python-version 3.12 --implementation cp --abi cp312 \
    #     --platform manylinux_2_27_x86_64 --platform manylinux_2_27_aarch64 \
    #     --platform macosx_11_0_arm64 --platform macosx_10_13_x86_64 \
    #     -r <top-level-pins>.in
    #
    # and read the resolved name==version pairs out of r.json.

    base = [
        ("pyyaml", "6.0.3"),    # Security patch (CVE-2024-...), stable
        ("pip", "26.2.1"),       # 6 CVEs fixed (path traversal, symlink, tar/zip, entry point)
    ]
    test_extra = [
        ("pytest", "9.1.1"),     # CVE-2025-71176 tmpdir handling fix
        ("pluggy", "1.7.0"),     # closure: pytest
        ("iniconfig", "2.3.1"),  # closure: pytest
        ("packaging", "26.3"),   # closure: pytest
        ("pygments", "2.21.0"),  # closure: pytest
        ("colorama", "0.4.6"),   # closure: pytest, win32 only; pip's resolver hides it
        ("coverage", "7.16.0"),  # Latest stable
        ("numpy", "2.5.2"),      # Latest stable, all OSV vulns fixed
    ]
    lint_extra = [
        ("ruff", "0.16.5"),      # Latest stable
    ]
    typecheck_extra = [
        ("mypy", "2.3.1"),       # Latest stable, all OSV vulns fixed
        ("typing_extensions", "4.16.0"),  # closure: mypy
        ("mypy_extensions", "1.2.0"),     # closure: mypy
        ("pathspec", "1.1.1"),            # closure: mypy
        ("librt", "0.16.0"),              # closure: mypy
        ("ast-serialize", "0.13.1"),      # closure: mypy
    ]

    write_reqs("requirements-ci-base.txt", "Base CI requirements (pyyaml + pip upgrade)", base)
    write_reqs("requirements-ci-test.txt", "Test runner requirements (base + pytest + coverage + numpy)", base + test_extra)
    write_reqs("requirements-ci-lint.txt", "Lint requirements (base + ruff)", base + lint_extra)
    write_reqs("requirements-ci-typecheck.txt", "Type-check requirements (base + mypy)", base + typecheck_extra)
    write_reqs("requirements-ci-fuzz.txt", "Fuzz/kernels requirements (pyyaml only)", [("pyyaml", "6.0.3")])


if __name__ == "__main__":
    main()
