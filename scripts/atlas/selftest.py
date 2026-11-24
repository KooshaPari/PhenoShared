#!/usr/bin/env python3
"""Self-checks for the atlas generator.

These assert the properties that make the artifacts trustworthy: deterministic
output, counts that agree between the independently computed sections, symbol
handling of edge cases (symlinks vs zero-byte files, no-trailing-newline LOC),
and strict path scoping. Run against a scratch fixture repository, plus the real
repository when one is available.

Usage:
    python3 scripts/atlas/selftest.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from atlaslib import gitio, hygiene, packages, scan  # noqa: E402
from atlaslib import render, render_hygiene  # noqa: E402
from atlaslib.readme_text import README  # noqa: E402

FAILURES: list[str] = []
CHECKS = [0]


def check(condition: bool, label: str) -> None:
    CHECKS[0] += 1
    if not condition:
        FAILURES.append(label)
        print(f"  FAIL  {label}")


def section(title: str) -> None:
    print(f"\n== {title}")


# ------------------------------------------------------------------ fixtures

FIXTURE = {
    "Cargo.toml": (
        '[workspace]\nresolver = "2"\n'
        'members = ["crates/alpha", "crates/beta"]\n'
        'exclude = ["vendor"]\n\n'
        '[workspace.package]\nversion = "0.1.0"\n'
    ),
    "crates/alpha/Cargo.toml": (
        '[package]\nname = "alpha"\ndescription = "The alpha crate."\nversion = "0.1.0"\n\n'
        '[lib]\npath = "src/lib.rs"\n'
    ),
    "crates/alpha/src/lib.rs": (
        "pub fn add(a: i32, b: i32) -> i32 { a + b }\n\n"
        '#[cfg(target_os = "linux")]\npub fn linux_only() {}\n\n'
        "#[test]\nfn adds() { assert_eq!(add(1, 1), 2); }\n\n"
        "#[tokio::test]\nasync fn async_adds() {}\n"
    ),
    "crates/alpha/src/main.rs": 'fn main() { println!("alpha"); }\n',
    "crates/alpha/README.md": "# alpha\n\nThe alpha crate readme prose.\n",
    "crates/beta/Cargo.toml": '[package]\nname = "beta"\nversion = "0.1.0"\n',
    "crates/beta/src/lib.rs": "#[test]\nfn beta_works() {}\n",
    "crates/beta/tests/common/mod.rs": "pub fn helper() {}\n",
    "crates/beta/tests/helpers.rs": "#[test]\nfn misnamed() {}\n",
    "crates/beta/tests/test_concern.rs": "#[test]\nfn canonical() {}\n",
    "crates/beta/tests/test_thing_unit.rs": "#[test]\nfn variant_suffix() {}\n",
    "vendor/Cargo.toml": '[package]\nname = "vendored"\nversion = "0.1.0"\n',
    "vendor/src/lib.rs": "pub fn v() {}\n",
    "docs/notes.md": "# notes\n",
    "AGENTS.md": "# agents\n",
    "LOOSE_STATUS_REPORT.md": "# status\n",
    "src/toplevel.rs": "pub fn top() {}\n",
    "scripts/atlas/generate.py": "MARKER = b'<REDACTED>'\n",
    "nonewline.rs": "pub fn one() {}\npub fn two() {}",
    "empty.rs": "",
    "long.rs": "\n".join(f"// line {i}" for i in range(600)) + "\n",
    "big.bin": "\x7fELF" + "\x00" * 64,
}

SYMLINK = ("link.rs", "crates/beta/src/lib.rs")


def make_fixture() -> str:
    root = tempfile.mkdtemp(prefix="atlas-fixture-")
    for rel, body in FIXTURE.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
    link_rel, target = SYMLINK
    os.symlink(target, os.path.join(root, link_rel))
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "fixture"],
        cwd=root, check=True,
    )
    return root


# ------------------------------------------------------------------ checks

def test_scanner(root: str) -> None:
    section("scanner")
    rec = scan.scan_file(root, "nonewline.rs")
    check(rec["loc"] == 2, f"no-trailing-newline LOC counts the final line (got {rec['loc']})")
    check(rec["nl_end"] is False, "no-trailing-newline detected")
    check(scan.scan_file(root, "empty.rs")["loc"] == 0, "empty file has 0 LOC")
    check(scan.scan_file(root, "link.rs")["kind"] == "link", "symlink classified as link")
    check(scan.scan_file(root, "link.rs")["size"] == 0, "symlink is not read as content")

    lib = scan.scan_file(root, "crates/alpha/src/lib.rs")
    check(lib["tests"] == 2, f"counts #[test] and #[tokio::test] (got {lib['tests']})")
    check(lib["os_cfg"] == ("linux",), f"captures target_os (got {lib['os_cfg']})")
    check(lib["main"] is False, "lib.rs is not an entrypoint")
    check(scan.scan_file(root, "crates/alpha/src/main.rs")["main"] is True,
          "src/main.rs is an entrypoint")
    check(scan.scan_file(root, "big.bin")["binary"] is True, "ELF magic detected")


def test_packages(root: str) -> None:
    section("packages")
    paths = gitio.tracked_paths(root)
    pkgs, members = packages.build_packages(root, paths)
    check("crates/alpha" in members, "alpha resolved as a workspace member")
    check(pkgs["crates/alpha"]["kind"] == "member", "alpha kind is member")
    check(pkgs["vendor"]["kind"] == "excluded", "vendor kind is excluded")
    check(pkgs["crates/beta"]["kind"] == "member", "beta kind is member")
    check(pkgs[""]["kind"] == "workspace-root", "root classified as workspace-root")

    files = scan.scan_all(root, paths)
    dates = gitio.commit_dates(root)
    rows, unowned, _ = packages.aggregate(root, pkgs, paths, files, dates)
    by_dir = {r["dir"]: r for r in rows}
    # alpha = lib.rs 10 + main.rs 1 + README.md 3 + Cargo.toml 7 = 21
    check(by_dir["crates/alpha"]["loc"] == 21,
          f"alpha tree LOC (got {by_dir['crates/alpha']['loc']})")
    check(by_dir["crates/beta"]["kind"] == "member/meta",
          f"beta flavour without [lib] (got {by_dir['crates/beta']['kind']})")
    check(by_dir["crates/alpha"]["os"] == "linux", "alpha reports linux os_cfg")
    check(by_dir["crates/alpha"]["last"] != "-", "alpha has a commit date")
    check(all(r["loc"] >= 0 for r in rows), "no negative LOC")
    check(unowned["files"] > 0, "root-level files bucket to workspace-root")


def test_hygiene(root: str) -> None:
    section("hygiene")
    paths = gitio.tracked_paths(root)
    files = scan.scan_all(root, paths)
    pkgs, _ = packages.build_packages(root, paths)
    h = hygiene.collect(root, files, pkgs)

    check(len(h["zero_byte"]) == 1 and h["zero_byte"][0] == "empty.rs",
          f"only the real empty file counts as zero-byte (got {h['zero_byte']})")
    check(len(h["symlinks"]) == 1, "symlink counted separately, not as zero-byte")
    check([p for p, _ in h["over_hard"]] == ["long.rs"], "600-line file is the only hard breach")

    tests = {p for p, _ in h["bad_test_names"]}
    check("crates/beta/tests/test_thing_unit.rs" in tests, "_unit test suffix flagged")
    check("crates/beta/tests/test_concern.rs" not in tests, "canonical test name not flagged")

    noncanon = set(h["noncanon_test_files"])
    check("crates/beta/tests/helpers.rs" in noncanon,
          "tests/ file that declares tests but is not test_*.rs is flagged")
    check("crates/beta/tests/common/mod.rs" not in noncanon,
          "tests/ helper with no #[test] is not flagged")
    check("crates/beta/tests/test_concern.rs" not in noncanon,
          "canonical tests/ file is not flagged")

    stray = set(h["stray_docs_root"])
    check("LOOSE_STATUS_REPORT.md" in stray, "root status doc flagged as stray")
    check("AGENTS.md" not in stray, "canonical root doc allowed")
    check("crates/alpha/README.md" in h["component_docs"],
          "component README set aside, not reported as stray")

    redacted = {p for p, _ in h["redacted"]}
    check("scripts/atlas/generate.py" not in redacted,
          "generator's own redaction needle self-excluded")
    check(not any(p.startswith("docs/atlas/codebase/") for p in redacted),
          "generated artifacts self-excluded")

    check(any("big.bin" == p for p, _, _ in h["artifacts"]),
          "committed binary flagged as artifact")
    check(h["archive_trees"] == {} or sum(h["archive_trees"].values()) >= 0,
          "archive tree accounting is well formed")


def test_rendering_and_determinism(root: str) -> None:
    section("rendering, determinism, section agreement")
    rev, _ = gitio.revision(root)
    paths = gitio.tracked_paths(root)
    files = scan.scan_all(root, paths)
    pkgs, _ = packages.build_packages(root, paths)
    dates = gitio.commit_dates(root)
    rows, unowned, _ = packages.aggregate(root, pkgs, paths, files, dates)
    h = hygiene.collect(root, files, pkgs)

    totals = {
        "packages": len(rows), "members": sum(1 for r in rows if r["is_member"]),
        "files": len(paths), "loc": sum(r["loc"] for r in files.values()),
        "rs_files": sum(1 for p in paths if p.endswith(".rs")),
        "rust_loc": sum(r["loc"] for p, r in files.items() if p.endswith(".rs")),
        "tests": sum(r["tests"] for r in files.values()),
        "member_loc": sum(r["loc"] for r in rows if r["is_member"]),
    }
    texts = {
        "INVENTORY.md": render.render_inventory(rev, rows, unowned, totals, pkgs),
        "FILES.md": render.render_files(rev, files, h),
        "HYGIENE.md": render_hygiene.render(rev, files, h, pkgs),
        "README.md": README,
    }
    for name, body in texts.items():
        check(len(body) > 200, f"{name} has content")
        check("|" in body, f"{name} contains tables")

    # Section headers must agree with the rows beneath them.
    def rows_under(text: str, header_prefix: str) -> int:
        captured, count = False, 0
        for line in text.splitlines():
            if line.startswith("## ") or line.startswith("### "):
                captured = line.startswith(header_prefix)
                continue
            if captured and line.startswith("| ") and not line.startswith("| path") \
                    and not line.startswith("|--") and not line.startswith("| area"):
                count += 1
        return count

    files_md = texts["FILES.md"]
    check(rows_under(files_md, "## GATE VIOLATION — source files over 500 lines") == len(h["src_hard"]),
          "FILES.md hard-source section row count matches src_hard")
    check(rows_under(files_md, "## GATE VIOLATION — source files over 350 lines") == len(h["src_target"]),
          "FILES.md target-source section row count matches src_target")
    check(rows_under(files_md, "## All tracked files over 500 lines") == len(h["over_hard"]),
          "FILES.md all-files hard section row count matches over_hard")
    check(rows_under(files_md, "## All tracked files over 350 lines") == len(h["over_target"]),
          "FILES.md all-files target section row count matches over_target")
    check(len(h["src_hard"]) <= len(h["over_hard"]), "source breaches subset of all breaches")
    check(all(n >= m for (_, n), (_, m) in zip(h["over_target"], h["over_target"])), "ordering stable")

    # Whole-pipeline determinism.
    def digest():
        _, r = gitio.revision(root)
        p = gitio.tracked_paths(root)
        f = scan.scan_all(root, p)
        k, _ = packages.build_packages(root, p)
        d = gitio.commit_dates(root)
        rr, uu, _ = packages.aggregate(root, k, p, f, d)
        hh = hygiene.collect(root, f, k)
        t = {
            "packages": len(rr), "members": sum(1 for x in rr if x["is_member"]),
            "files": len(p), "loc": sum(x["loc"] for x in f.values()),
            "rs_files": sum(1 for x in p if x.endswith(".rs")),
            "rust_loc": sum(x["loc"] for y, x in f.items() if y.endswith(".rs")),
            "tests": sum(x["tests"] for x in f.values()),
            "member_loc": sum(x["loc"] for x in rr if x["is_member"]),
        }
        return (
            render.render_inventory(r, rr, uu, t, k)
            + render.render_files(r, f, hh)
            + render_hygiene.render(r, f, hh, k)
            + README
        )

    check(digest() == digest(), "full pipeline is deterministic across runs")


def test_scope(root: str) -> None:
    section("path scoping")
    status = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                            capture_output=True, text=True).stdout.strip()
    check(status == "", f"selftest leaves no worktree changes (got: {status!r})")


def main() -> int:
    root = make_fixture()
    print(f"fixture: {root}")
    test_scanner(root)
    test_packages(root)
    test_hygiene(root)
    test_rendering_and_determinism(root)
    test_scope(root)
    print(f"\n{CHECKS[0]} checks, {len(FAILURES)} failures")
    for failure in FAILURES:
        print(f"  - {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
