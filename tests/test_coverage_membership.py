"""Regression tests for the root-workspace coverage membership guard.

The guard is `.github/scripts/coverage_membership.py`. It makes every
workspace member either measured by exactly one coverage group or explicitly
excused in `.coverage-baselines/membership.toml`, so a member can no longer
enter the workspace and vanish from the coverage gate without a word.

The tests below use a FAKE cargo metadata document, a fake workflow and a fake
ledger, so they are fast and deterministic: none of them depends on the real
291-member workspace. The last test does run the guard against the real
repository inputs, because "the real workspace is fully accounted for" is the
property this change actually claims.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "coverage_membership.py"
REAL_LEDGER = REPO_ROOT / ".coverage-baselines" / "membership.toml"
REAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "coverage.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("coverage_membership", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


membership = _load_module()

WORKFLOW_HEADER = """\
name: Coverage Gate
on: [push]
jobs:
  coverage-root-group:
    strategy:
      matrix:
        include:
"""


def workflow_text(groups):
    """A fake coverage workflow with the given {group: [packages]} matrix."""
    entries = ""
    for name, packages in groups.items():
        entries += f"          - group: {name}\n"
        entries += f"            packages: '{' '.join(packages)}'\n"
    return WORKFLOW_HEADER + entries


def metadata_document(root, packages):
    """A fake cargo metadata document for (name, directory) packages."""
    ids, members = {}, []
    for index, (name, directory) in enumerate(packages):
        ids[name] = f"path+file://{root}/{directory}#name={name}@{index}"
        members.append(ids[name])
    return {
        "workspace_root": str(root),
        "workspace_members": members,
        "packages": [
            {
                "id": ids[name],
                "name": name,
                "manifest_path": os.path.join(str(root), directory, "Cargo.toml"),
            }
            for name, directory in packages
        ],
    }


def ledger_text(meta, excuses):
    """A fake membership ledger."""
    lines = ["[meta]"]
    for key, value in meta.items():
        lines.append(f"{key} = {value}")
    lines.append("")
    lines.append("[excused]")
    for name, reason in excuses.items():
        lines.append(f'"{name}" = """')
        lines.append(reason)
        lines.append('"""')
    lines.append("")
    return "\n".join(lines)


class FakeWorkspace:
    """A throwaway repository root with metadata, workflow and ledger files."""

    def __init__(self, packages, groups, ledger):
        self._temp = tempfile.TemporaryDirectory(prefix="coverage-membership-")
        self.root = Path(self._temp.name)
        self.metadata = self.root / "metadata.json"
        self.workflow = self.root / "coverage.yml"
        self.ledger = self.root / "membership.toml"
        self.metadata.write_text(
            json.dumps(metadata_document(self.root, packages)), encoding="utf-8"
        )
        self.workflow.write_text(workflow_text(groups), encoding="utf-8")
        self.ledger.write_text(ledger, encoding="utf-8")

    def close(self):
        self._temp.cleanup()

    def run(self):
        """Run the guard against this workspace. Returns (exit code, output)."""
        argv = [
            "--root",
            str(self.root),
            "--metadata",
            str(self.metadata),
            "--workflow",
            str(self.workflow),
            "--ledger",
            str(self.ledger),
        ]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = membership.main(argv)
        return code, out.getvalue() + err.getvalue()


class MembershipGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspaces = []

    def tearDown(self) -> None:
        for workspace in self.workspaces:
            workspace.close()

    def workspace(self, packages, groups, meta, excuses):
        workspace = FakeWorkspace(packages, groups, ledger_text(meta, excuses))
        self.workspaces.append(workspace)
        return workspace

    def test_member_in_no_group_and_no_ledger_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha"]},
            meta={"total_members": 2, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("beta", output)
        self.assertIn("owned by no group", output)

    def test_member_excused_with_a_reason_passes(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha"]},
            meta={"total_members": 2, "measured_members": 1, "excused_members": 1},
            excuses={"beta": "measured by a lane that does not exist yet"},
        )
        code, output = workspace.run()
        self.assertEqual(code, 0, output)
        self.assertIn("OK", output)

    def test_member_in_two_groups_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha", "beta"], "two": ["beta"]},
            meta={"total_members": 2, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("counted twice", output)
        self.assertIn("beta", output)

    def test_member_in_exactly_one_group_passes(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha"], "two": ["beta"]},
            meta={"total_members": 2, "measured_members": 2, "excused_members": 0},
            excuses={},
        )
        code, output = workspace.run()
        self.assertEqual(code, 0, output)
        self.assertIn("OK", output)

    def test_excuse_with_an_empty_reason_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha"]},
            meta={"total_members": 2, "measured_members": 1, "excused_members": 1},
            excuses={"beta": "   "},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("empty reason", output)

    def test_stale_ledger_entry_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha")],
            groups={"one": ["alpha"]},
            meta={"total_members": 1, "measured_members": 1, "excused_members": 0},
            excuses={"gone": "this member no longer exists"},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("stale", output)

    def test_group_listing_a_non_member_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha")],
            groups={"one": ["alpha", "ghost"]},
            meta={"total_members": 1, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("ghost", output)

    def test_meta_count_mismatch_fails(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha"), ("beta", "crates/beta")],
            groups={"one": ["alpha"]},
            meta={"total_members": 2, "measured_members": 1, "excused_members": 0},
            excuses={"beta": "a reason"},
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("excused_members", output)

    def test_unparseable_ledger_fails_closed(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha")],
            groups={"one": ["alpha"]},
            meta={"total_members": 1, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        workspace.ledger.write_text(
            "[meta]\nthis line has no equals sign\n", encoding="utf-8"
        )
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("could not run", output)

    def test_unparseable_workflow_fails_closed(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha")],
            groups={"one": ["alpha"]},
            meta={"total_members": 1, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        workspace.workflow.write_text("jobs: [unclosed\n", encoding="utf-8")
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("could not run", output)

    def test_missing_ledger_fails_closed(self) -> None:
        workspace = self.workspace(
            packages=[("alpha", "crates/alpha")],
            groups={"one": ["alpha"]},
            meta={"total_members": 1, "measured_members": 1, "excused_members": 0},
            excuses={},
        )
        workspace.ledger.unlink()
        code, output = workspace.run()
        self.assertEqual(code, 1)
        self.assertIn("could not run", output)

    @unittest.skipUnless(shutil.which("cargo"), "cargo is not installed")
    def test_real_workspace_is_fully_accounted_for(self) -> None:
        """The real workspace passes: every member is measured or excused."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = membership.main(
                [
                    "--root",
                    str(REPO_ROOT),
                    "--workflow",
                    str(REAL_WORKFLOW),
                    "--ledger",
                    str(REAL_LEDGER),
                ]
            )
        output = out.getvalue() + err.getvalue()
        self.assertEqual(code, 0, output)
        self.assertIn("every workspace member", output)
        self.assertIn("291", output)


class MetadataLoadingTests(unittest.TestCase):
    """`load_metadata` reads cargo's stdout as the JSON document.

    cargo writes warnings and progress to stderr. Merging the two streams
    (``stderr=subprocess.STDOUT``) prepends that text to the JSON and makes a
    perfectly good run fail with "Expecting value: line 1 column 1", which says
    nothing about the real cause. This happened on PR #822's first run.
    """

    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="membership-metadata-")
        (Path(self.root) / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        self.bin = Path(self.root) / "bin"
        self.bin.mkdir()
        self._old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self._old_path}"

    def tearDown(self) -> None:
        os.environ["PATH"] = self._old_path
        shutil.rmtree(self.root, ignore_errors=True)

    def fake_cargo(self, *, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        script = self.bin / "cargo"
        script.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.stdout.write({stdout!r})\n"
            f"sys.stderr.write({stderr!r})\n"
            f"sys.exit({code})\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

    def test_warning_on_stderr_does_not_corrupt_the_json(self) -> None:
        payload = {"workspace_root": self.root, "workspace_members": [], "packages": []}
        self.fake_cargo(
            stdout=json.dumps(payload),
            stderr="warning: unused manifest key: patch\n",
        )
        meta = membership.load_metadata(self.root, None)
        self.assertEqual(meta["workspace_root"], self.root)

    def test_failure_reports_stderr_and_the_exit_code(self) -> None:
        self.fake_cargo(stderr="error: failed to load manifest\n", code=101)
        with self.assertRaises(membership.MembershipError) as caught:
            membership.load_metadata(self.root, None)
        message = str(caught.exception)
        self.assertIn("failed to load manifest", message)
        self.assertIn("101", message)

    def test_unparseable_json_surfaces_stderr_for_diagnosis(self) -> None:
        self.fake_cargo(stdout="not json at all", stderr="cargo said something\n")
        with self.assertRaises(membership.MembershipError) as caught:
            membership.load_metadata(self.root, None)
        message = str(caught.exception)
        self.assertIn("invalid JSON", message)
        self.assertIn("cargo said something", message)


if __name__ == "__main__":
    unittest.main()
