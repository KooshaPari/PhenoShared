"""Local Git regression tests for preserved source commit comparisons."""

import contextlib
import io
import os
import subprocess  # nosec B404 — test harness shelling out to the local git binary only
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_preserved as verifier


class PreservedTests(unittest.TestCase):
    def test_pin_and_live_source(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            env = dict(
                os.environ,
                GIT_AUTHOR_NAME="Test",
                GIT_AUTHOR_EMAIL="test@example.invalid",
                GIT_COMMITTER_NAME="Test",
                GIT_COMMITTER_EMAIL="test@example.invalid",
            )

            def git(*args, input=None):
                return subprocess.run(  # nosec B603 B607 — argv list, no shell, "git" from PATH by design
                    ["git", "-C", str(repo), *args],
                    input=input,
                    text=True,
                    capture_output=True,
                    check=True,
                    env=env,
                ).stdout.strip()

            git("init", "-q")
            (repo / "file").write_text("absorbed\n")
            git("add", "file")
            tree = git("write-tree")
            pinned = git("commit-tree", tree, "-m", "absorbed")
            (repo / "file").write_text("later upstream\n")
            git("add", "file")
            moved = git("commit-tree", git("write-tree"), "-p", pinned, "-m", "moved")
            git("update-ref", "refs/check/host-ops/heads/main", moved)
            unrelated = git("commit-tree", tree, "-m", "unreachable same tree")

            def graft(subtree):
                entry = "040000 tree %s\ttree\n" % subtree
                nested = git("mktree", input=entry)
                nested = git("mktree", input="040000 tree %s\thost-ops\n" % nested)
                root = git("mktree", input="040000 tree %s\trepos\n" % nested)
                commit = git("commit-tree", root, "-m", "registry")
                git("update-ref", "refs/check/main", commit)

            real_sh = verifier.sh

            def local_sh(args, cwd=None):
                if args[0] == "gh" or "fetch" in args:
                    return 0, "", ""
                args = list(args)
                args[2] = str(repo)
                return real_sh(args, cwd)

            def run(*args):
                output = io.StringIO()
                with patch.object(
                    sys, "argv", ["verify_preserved.py", "host-ops", *args]
                ), patch.object(verifier, "sh", side_effect=local_sh), patch.object(
                    verifier.tempfile, "mkdtemp", return_value=directory
                ), contextlib.redirect_stdout(
                    output
                ):
                    code = verifier.main()
                return code, output.getvalue()

            graft(tree)
            code, output = run("--at", pinned)
            self.assertEqual(code, 0)
            self.assertIn("at " + pinned, output)
            code, output = run()
            self.assertEqual(code, 1)
            self.assertIn(
                "source is live and may have moved; --at pins the comparison", output
            )
            self.assertEqual(run("--at", unrelated)[0], 1)
            self.assertEqual(run("--at", "does-not-exist")[0], 1)

            graft(
                git(
                    "mktree",
                    input="100644 blob %s\tabsent\n"
                    % git("hash-object", "-w", "--stdin", input="absent\n"),
                )
            )
            self.assertEqual(run()[0], 1)
            self.assertEqual(run("--at", pinned)[0], 1)

            graft(git("rev-parse", moved + "^{tree}"))
            code, output = run()
            self.assertEqual(code, 0)
            self.assertEqual(
                output,
                "%-24s tree %s == branch main\n\nmatched 1, unmatched 0\n"
                % ("host-ops", git("rev-parse", moved + "^{tree}")[:10]),
            )


if __name__ == "__main__":
    unittest.main()
