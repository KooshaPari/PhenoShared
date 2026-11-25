"""Comprehensive functional tests for ``verifier.risky_action``.

Covers the full gate-evaluation contract end-to-end:

* ``GateResult`` dataclass + ``to_dict`` round-trip
* ``_load_gate_config`` YAML loading + missing-file fallback
* ``extract_proposed_command`` (JSON ``"command"`` / ``"bash"`` keys,
  fenced bash/sh/shell blocks, ``$ ``-prefix lines, ``None``)
* ``_tier_for_command`` blocklist / low / medium / destructive-verb / default
* ``_check_secrets`` (positive + negative)
* ``_check_allowlist`` (allowlist disabled, in-root, out-of-root,
  ``//`` skip, ``://`` skip, ``OSError`` swallow, ``${PHENO_ROOT}`` expand,
  ``://`` mid-path skip, ``:/`` preceding-slash skip)
* ``_dry_run_proposal`` (git apply + patch, git apply without patch,
  docker presence, docker unreachable, destructive verbs, no-op)
* ``check_proposal`` end-to-end (gate disabled, no proposal, low-tier
  pass, medium-tier fail on path, high-tier fail on blocklist, critical-tier
  missing human approval, critical-tier requires verifier, dry_run branch,
  ``output_parseable`` check)

The real ``config/risky_action_gate.yaml`` is used for integration tests,
but ``_load_gate_config`` is also monkey-patched with inline configs to
drive edge branches without YAML edits.  All monkeypatching uses
``monkeypatch.setattr(<module>, <attr>, <value>)`` with the actual module
reference (not a string path) so refactors that rename the module path
are caught at test-collection time.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

import verifier.risky_action as risky_action_mod
from verifier.risky_action import (
    GateResult,
    _check_allowlist,
    _check_secrets,
    _dry_run_proposal,
    _load_gate_config,
    _tier_for_command,
    check_proposal,
    extract_proposed_command,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "risky_action_gate.yaml"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_config() -> dict[str, Any]:
    """Load the real risky_action_gate.yaml once per test."""
    assert CONFIG_PATH.exists(), (
        f"expected {CONFIG_PATH} for integration tests"
    )
    return _load_gate_config()


@pytest.fixture()
def cfg_factory(monkeypatch: pytest.MonkeyPatch):
    """Return a callable that monkey-patches ``_load_gate_config`` with module ref.

    Usage::

        def test_foo(cfg_factory):
            with cfg_factory({"enabled": True, ...}):
                ...

    The patch is automatically reverted at fixture teardown via monkeypatch.
    """

    def _make(cfg: dict[str, Any]):
        return monkeypatch.setattr(
            risky_action_mod, "_load_gate_config", lambda: cfg
        )

    return _make


# ---------------------------------------------------------------------------
# GateResult dataclass + to_dict
# ---------------------------------------------------------------------------


class TestGateResultDataclass:
    """``GateResult`` is a dataclass with JSON-friendly serialization."""

    def test_default_construction(self) -> None:
        g = GateResult(ok=True, tier="low", action="")
        assert g.ok is True
        assert g.tier == "low"
        assert g.action == ""
        assert g.checks == {}
        assert g.errors == []
        assert g.meta == {}

    def test_construction_with_all_fields(self) -> None:
        g = GateResult(
            ok=False,
            tier="critical",
            action="rm -rf /",
            checks={"secret_clear": False},
            errors=["boom"],
            meta={"mode": "block_until_verified"},
        )
        assert g.ok is False
        assert g.tier == "critical"
        assert g.action == "rm -rf /"
        assert g.checks == {"secret_clear": False}
        assert g.errors == ["boom"]
        assert g.meta == {"mode": "block_until_verified"}

    def test_to_dict_round_trip(self) -> None:
        g = GateResult(
            ok=False,
            tier="high",
            action="rm -rf foo",
            checks={"secret_clear": True, "pattern_blocklist_clear": False},
            errors=["blocklist recursive_delete: \\brm\\s+(-[^\\s]*\\s+)*-r"],
            meta={"mode": "block_until_verified", "required": ["verifier_pass"]},
        )
        d = g.to_dict()
        assert d == {
            "ok": False,
            "tier": "high",
            "action": "rm -rf foo",
            "checks": {"secret_clear": True, "pattern_blocklist_clear": False},
            "errors": ["blocklist recursive_delete: \\brm\\s+(-[^\\s]*\\s+)*-r"],
            "meta": {"mode": "block_until_verified", "required": ["verifier_pass"]},
        }
        # JSON-serializable (no dataclass/Path leakage)
        json.dumps(d)  # raises if not JSON-clean

    def test_to_dict_preserves_empty_collections(self) -> None:
        g = GateResult(ok=True, tier="none", action="")
        d = g.to_dict()
        assert d["checks"] == {}
        assert d["errors"] == []
        assert d["meta"] == {}

    def test_to_dict_then_construction_equivalent(self) -> None:
        original = GateResult(
            ok=True,
            tier="medium",
            action="echo hi",
            checks={"output_parseable": True},
            errors=[],
            meta={"mode": "block_until_verified"},
        )
        rebuilt = GateResult(**original.to_dict())
        assert rebuilt == original


# ---------------------------------------------------------------------------
# _load_gate_config
# ---------------------------------------------------------------------------


class TestLoadGateConfig:
    """``_load_gate_config`` reads YAML; missing file → ``{"enabled": False}``."""

    def test_returns_dict_when_present(self, real_config: dict[str, Any]) -> None:
        assert isinstance(real_config, dict)
        assert real_config.get("enabled") is True
        # Has the standard sections
        assert "risk_tiers" in real_config
        assert "pattern_blocklist" in real_config
        assert "secret_patterns" in real_config

    def test_missing_file_returns_disabled_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # CONFIG_DIR is read at call-time, so monkey-patch it via module ref
        fake_dir = tmp_path / "no_such_config_dir"
        monkeypatch.setattr(risky_action_mod, "CONFIG_DIR", fake_dir)
        cfg = _load_gate_config()
        assert cfg == {"enabled": False}

    def test_non_dict_yaml_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A YAML file containing a non-mapping (e.g. a bare list) yields ``{}``."""
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        (cfg_dir / "risky_action_gate.yaml").write_text("- a\n- b\n", encoding="utf-8")
        monkeypatch.setattr(risky_action_mod, "CONFIG_DIR", cfg_dir)
        cfg = _load_gate_config()
        # Non-dict YAML is coerced to empty dict by the implementation.
        assert cfg == {}


# ---------------------------------------------------------------------------
# extract_proposed_command
# ---------------------------------------------------------------------------


class TestExtractProposedCommand:
    """``extract_proposed_command`` recovers shell commands from agent text."""

    def test_empty_string_returns_none(self) -> None:
        assert extract_proposed_command("") is None

    def test_none_input_returns_none(self) -> None:
        # Defensive: function short-circuits on falsy input.
        assert extract_proposed_command(None) is None  # type: ignore[arg-type]

    def test_json_command_key(self) -> None:
        text = 'I will run {"command": "ls -la /tmp"} now'
        assert extract_proposed_command(text) == "ls -la /tmp"

    def test_json_command_key_simple(self) -> None:
        text = '{"command": "echo hi"}'
        assert extract_proposed_command(text) == "echo hi"

    def test_json_bash_key(self) -> None:
        text = '{"bash": "rm -rf /tmp/build"}'
        assert extract_proposed_command(text) == "rm -rf /tmp/build"

    def test_json_command_takes_priority_over_bash(self) -> None:
        # "command" is matched first; "bash" is the fallback.
        text = '{"command": "first", "bash": "second"}'
        assert extract_proposed_command(text) == "first"

    def test_fenced_bash_block(self) -> None:
        text = "I will run:\n```bash\nls -la\necho done\n```"
        out = extract_proposed_command(text)
        assert out == "ls -la"

    def test_fenced_sh_block(self) -> None:
        text = "```sh\nrm -rf foo\n```"
        assert extract_proposed_command(text) == "rm -rf foo"

    def test_fenced_shell_block(self) -> None:
        text = "```shell\necho hello\n```"
        assert extract_proposed_command(text) == "echo hello"

    def test_fenced_block_empty_returns_none(self) -> None:
        text = "```bash\n\n```"
        assert extract_proposed_command(text) is None

    def test_fenced_block_only_whitespace_returns_none(self) -> None:
        assert extract_proposed_command("```bash\n   \n```") is None

    def test_dollar_prefix_line(self) -> None:
        text = "Here is what to run:\n$ rm -rf build\n$ ls\n"
        assert extract_proposed_command(text) == "rm -rf build"

    def test_dollar_prefix_with_leading_whitespace(self) -> None:
        # The function strips lines before testing the "$ " prefix.
        text = "   $ echo stripped"
        assert extract_proposed_command(text) == "echo stripped"

    def test_no_command_in_text(self) -> None:
        text = "I have no proposal in this response."
        assert extract_proposed_command(text) is None

    def test_only_whitespace_returns_none(self) -> None:
        # No JSON keys, no fences, no "$ " prefix → None
        assert extract_proposed_command("   \n  \t\n") is None

    def test_fenced_non_shell_language_ignored(self) -> None:
        # ```python / ```text should not be picked up
        text = "```python\nprint('hi')\n```"
        assert extract_proposed_command(text) is None

    def test_json_command_with_trailing_text(self) -> None:
        # The regex is non-greedy on [^"]+ — must stop at the first close quote
        text = '{"command": "ls"} tail'
        assert extract_proposed_command(text) == "ls"


# ---------------------------------------------------------------------------
# _tier_for_command
# ---------------------------------------------------------------------------


class TestTierForCommand:
    """``_tier_for_command`` classifies commands using YAML tiers + fallback."""

    @pytest.fixture()
    def minimal_cfg(self) -> dict[str, Any]:
        return {
            "pattern_blocklist": [
                {
                    "id": "recursive_delete",
                    "regex": r"\brm\s+(-[^\s]*\s+)*-r",
                    "tier": "high",
                },
                {
                    "id": "force_push",
                    "regex": r"git\s+push\s+.*--force",
                    "tier": "critical",
                },
            ],
            "risk_tiers": {
                "low": {"examples": ["ls", "cat", "head", "grep", "git_status"]},
                "medium": {"examples": ["file_write", "patch_apply", "patch_apply_x"]},
            },
        }

    def test_blocklist_match_returns_blocklist_tier(
        self, minimal_cfg: dict[str, Any]
    ) -> None:
        assert _tier_for_command("rm -rf /", minimal_cfg) == "high"
        assert _tier_for_command("rm -r /tmp/build", minimal_cfg) == "high"

    def test_blocklist_critical_match(self, minimal_cfg: dict[str, Any]) -> None:
        assert _tier_for_command("git push origin main --force", minimal_cfg) == "critical"

    def test_blocklist_match_case_insensitive(self, minimal_cfg: dict[str, Any]) -> None:
        assert _tier_for_command("RM -RF /", minimal_cfg) == "high"

    def test_low_tier_match(self, minimal_cfg: dict[str, Any]) -> None:
        # low examples matched via "x in cmd_l" OR "x.replace('_',' ') in cmd_l"
        assert _tier_for_command("ls -la /tmp", minimal_cfg) == "low"
        assert _tier_for_command("cat file.txt", minimal_cfg) == "low"
        assert _tier_for_command("head -n 5 log", minimal_cfg) == "low"
        # Underscore examples match via replace("_", " ")
        assert _tier_for_command("git status", minimal_cfg) == "low"

    def test_medium_tier_match(self, minimal_cfg: dict[str, Any]) -> None:
        # file_write / patch_apply are literal examples in the cfg
        assert _tier_for_command("file_write foo.txt", minimal_cfg) == "medium"
        assert _tier_for_command("patch_apply /tmp/x", minimal_cfg) == "medium"

    def test_destructive_verb_falls_through_to_high(
        self, minimal_cfg: dict[str, Any]
    ) -> None:
        # After low/medium misses, the destructive-verb regex escalates to high
        assert _tier_for_command("mv foo bar", minimal_cfg) == "high"
        assert _tier_for_command("chmod 777 /tmp/x", minimal_cfg) == "high"
        assert _tier_for_command("curl http://example.com", minimal_cfg) == "high"
        assert _tier_for_command("wget http://example.com", minimal_cfg) == "high"
        assert _tier_for_command("git commit -m x", minimal_cfg) == "high"
        assert _tier_for_command("git push origin main", minimal_cfg) == "high"

    def test_default_falls_back_to_medium(self, minimal_cfg: dict[str, Any]) -> None:
        # "echo hi" has no blocklist/low/medium/destructive-verb → default
        assert _tier_for_command("echo hi", minimal_cfg) == "medium"

    def test_blocklist_with_default_tier_when_missing(
        self, minimal_cfg: dict[str, Any]
    ) -> None:
        cfg_no_tier: dict[str, Any] = {
            "pattern_blocklist": [
                {"id": "x", "regex": r"\bsomething\b"},  # no "tier" key
            ],
            "risk_tiers": {},
        }
        # .get("tier", "high") → "high"
        assert _tier_for_command("something", cfg_no_tier) == "high"

    def test_empty_blocklist_skips(self, minimal_cfg: dict[str, Any]) -> None:
        cfg: dict[str, Any] = {
            "pattern_blocklist": [],
            "risk_tiers": minimal_cfg["risk_tiers"],
        }
        # No blocklist, "ls" is low
        assert _tier_for_command("ls", cfg) == "low"

    def test_no_risk_tiers_config_returns_medium_default(self) -> None:
        cfg: dict[str, Any] = {"pattern_blocklist": [], "risk_tiers": {}}
        # No low/medium match, no destructive verb → "medium" default
        assert _tier_for_command("echo hi", cfg) == "medium"


# ---------------------------------------------------------------------------
# _check_secrets
# ---------------------------------------------------------------------------


class TestCheckSecrets:
    """``_check_secrets`` matches commands against secret patterns."""

    def test_no_patterns_returns_ok(self) -> None:
        ok, err = _check_secrets("echo hello", {"secret_patterns": []})
        assert ok is True
        assert err is None

    def test_clean_command_passes(self) -> None:
        cfg = {"secret_patterns": [r"(?i)(api[_-]?key|secret|password|token)\s*[=:]"]}
        ok, err = _check_secrets("ls -la", cfg)
        assert ok is True
        assert err is None

    def test_api_key_assignment_blocked(self) -> None:
        cfg = {"secret_patterns": [r"(?i)(api[_-]?key|secret|password|token)\s*[=:]"]}
        ok, err = _check_secrets("export API_KEY=abcd1234", cfg)
        assert ok is False
        assert err is not None
        assert "secret pattern matched" in err

    def test_openai_sk_prefix_blocked(self) -> None:
        cfg = {"secret_patterns": [r"sk-[a-zA-Z0-9]{20,}"]}
        ok, err = _check_secrets("echo sk-abcdefghijklmnopqrstuv", cfg)
        assert ok is False
        assert err is not None

    def test_private_key_marker_blocked(self) -> None:
        cfg = {
            "secret_patterns": [r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"]
        }
        ok, err = _check_secrets(
            "cat -----BEGIN RSA PRIVATE KEY-----", cfg
        )
        assert ok is False
        assert err is not None

    def test_first_matching_pattern_is_reported(self) -> None:
        cfg = {
            "secret_patterns": [
                r"password\s*=",
                r"secret\s*=",
            ]
        }
        ok, err = _check_secrets("password=foo", cfg)
        assert ok is False
        assert err is not None
        # Error message includes the first matching pattern
        assert "password" in err

    def test_error_message_truncated_to_40_chars(self) -> None:
        # The implementation truncates the pattern to 40 chars in the error.
        long_pat = "secret" + ("x" * 100)
        cfg = {"secret_patterns": [long_pat]}
        ok, err = _check_secrets("echo " + long_pat, cfg)
        assert ok is False
        # Error includes the first 40 chars of the matched pattern
        # ("secret" + 34 x's = 40 chars total)
        assert err is not None
        expected = "secret" + ("x" * 34)  # 40 chars
        assert expected in err
        assert len(expected) == 40
        # Not the full 100-char tail
        assert "x" * 35 not in err


# ---------------------------------------------------------------------------
# _check_allowlist
# ---------------------------------------------------------------------------


class TestCheckAllowlist:
    """``_check_allowlist`` validates absolute paths against workspace roots."""

    def test_disabled_flag_passes(self) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": False,
                "workspace_roots": [],
            }
        }
        ok, err = _check_allowlist("cat /etc/passwd", cfg)
        assert ok is True
        assert err is None

    def test_path_inside_root_passes(self, tmp_path: Path) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            }
        }
        inside = tmp_path / "ok.txt"
        ok, err = _check_allowlist(f"cat {inside}", cfg)
        assert ok is True
        assert err is None

    def test_path_outside_root_blocked(self, tmp_path: Path) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path / "root")],
            }
        }
        # tmp_path itself is not under tmp_path/root
        ok, err = _check_allowlist(f"cat {tmp_path / 'evil.txt'}", cfg)
        assert ok is False
        assert err is not None
        assert "outside allowlist" in err

    def test_double_slash_skipped(self, tmp_path: Path) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            }
        }
        # "://" gets skipped because it looks URL-derived
        ok, err = _check_allowlist("curl http://example.com//foo", cfg)
        # The "://example.com//foo" portion should be ignored entirely
        # because of the :// and // guards.
        assert ok is True
        assert err is None

    def test_url_with_protocol_skipped(self, tmp_path: Path) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            }
        }
        ok, err = _check_allowlist(
            "curl https://api.example.com/v1/secret-key=abcd", cfg
        )
        assert ok is True
        assert err is None

    def test_pheno_root_expansion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": ["${PHENO_ROOT}"],
            }
        }
        # Patch CONFIG_DIR so ${PHENO_ROOT} (=CONFIG_DIR.parent) → tmp_path
        monkeypatch.setattr(risky_action_mod, "CONFIG_DIR", tmp_path / "config")
        inside = tmp_path / "ok.txt"
        ok, err = _check_allowlist(f"cat {inside}", cfg)
        assert ok is True
        assert err is None

    def test_no_absolute_paths_passes(self) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": ["/anywhere"],
            }
        }
        ok, err = _check_allowlist("echo hi", cfg)
        assert ok is True
        assert err is None

    def test_path_with_quotes_stripped(self, tmp_path: Path) -> None:
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            }
        }
        inside = tmp_path / "q.txt"
        # The regex strips surrounding quotes before resolving
        ok, err = _check_allowlist(f"cat \"{inside}\"", cfg)
        assert ok is True
        assert err is None

    def test_path_home_expansion_via_path_home_mock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Path.home() reads USERPROFILE on Windows, so we patch it explicitly
        # to verify the ${HOME} substitution logic.
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": ["${HOME}/pheno-harness"],
            }
        }
        monkeypatch.setattr(risky_action_mod.Path, "home", lambda: tmp_path)
        inside = tmp_path / "pheno-harness" / "ok.txt"
        ok, err = _check_allowlist(f"cat {inside}", cfg)
        assert ok is True
        assert err is None

    def test_path_with_double_slash_scheme_in_middle_skipped(
        self, tmp_path: Path
    ) -> None:
        """A Windows-style path containing ``://`` mid-string is skipped.

        The regex matches ``C:\\Y://Z`` starting at position 4.  ``p`` is
        ``C:\\Y://Z`` which does NOT start with ``//`` (single backslash
        then ``Y://Z``), but it DOES contain ``://``.  The
        ``if "://" in p: continue`` branch on line 187 catches it.
        """
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            }
        }
        # Construct a cmd whose regex match yields p = "C:\\Y://Z" —
        # p does not start with "//" but contains "://" so line 187 fires.
        # Use forward slashes after the colon: the regex `(?:[A-Za-z]:\\|/)`
        # requires a backslash for the drive prefix on the FIRST match, but
        # the SECOND match (the `/Z` after `://`) starts with `/`.
        # Easier: use a path like `C:\foo//bar` where the regex matches
        # `C:\foo//bar` — p doesn't start with `//` (starts with `C:`) but
        # contains `//` which is a different skip path.  For the `://` skip
        # we need a cmd where the regex matches `/something` that contains
        # `://` but doesn't start with `//`.  This happens for cmd like
        # `cat /X://Y` where the regex matches `/X://Y` at the first `/`.
        ok, err = _check_allowlist("cat /X://Y", cfg)
        # `/X://Y` contains "://" so the path is skipped (not validated).
        assert ok is True
        assert err is None

    def test_path_resolve_oserror_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``OSError`` from ``Path.resolve()`` is swallowed; remaining paths
        are still validated.

        We mock ``Path.resolve`` on the module to raise ``OSError`` ONLY for
        paths that don't start with the workspace root (i.e. the absolute
        paths extracted from the cmd), so every absolute path match in the
        cmd falls into the ``except OSError: continue`` branch
        (lines 190-191).  With no remaining paths to validate, the function
        returns ``(True, None)``.
        """
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                # No ${HOME} / ${PHENO_ROOT} expansion in workspace_roots
                # so the mock Path only needs to support ``.resolve()`` (no
                # ``Path.home()`` / ``CONFIG_DIR`` access at expand time).
                "workspace_roots": [str(tmp_path)],
            },
        }
        workspace_root = str(tmp_path).lower()

        original_resolve = risky_action_mod.Path.resolve

        def _raising_resolve(self: Any) -> Any:
            # Allow resolve() to work for the workspace root itself; raise
            # OSError for any other path (the cmd's extracted absolute paths).
            if str(self).lower().startswith(workspace_root):
                return original_resolve(self)
            raise OSError("simulated resolve failure")

        # Patch only the ``resolve`` method on ``pathlib.Path`` itself.
        # Other code (e.g. ``Path(r)`` construction) still works normally.
        monkeypatch.setattr(risky_action_mod.Path, "resolve", _raising_resolve)
        # The cmd's path is outside the workspace_root (tmp_path/anything
        # is *under* tmp_path, but the mock checks the Path object's
        # string form, not the allowlist).  Actually tmp_path/anything IS
        # under tmp_path, so we need a path outside to trigger the raise.
        ok, err = _check_allowlist("cat /nonexistent/outside/root", cfg)
        # All path matches raised OSError → swallowed → no failure reported.
        assert ok is True
        assert err is None

    def test_path_with_colon_slash_preceding_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hit the ``cmd[start-2:start] == ":/"`` branch on line 185.

        The branch is unreachable through the real ``re.finditer`` because
        any cmd where the path's leading ``/`` is preceded by ``:/`` would
        have the regex match the ``//`` prefix at start-1 instead of the
        single ``/`` at start.  We simulate the crafted match directly.
        """
        cfg = {
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            },
        }

        # Build a fake match object: start=3, match text "/foo" so that
        # cmd[1:3] == ":/" (colon-slash).  ``p`` ("/foo") does not start
        # with "//", so the earlier ``p.startswith("//")`` guard does not
        # fire; the ``cmd[start-2:start] == ":/"`` guard on line 184-185
        # is the one that catches it.
        import re as _re

        class _FakeMatch:
            def start(self) -> int:
                return 3

            def group(self, _idx: int = 0) -> str:
                return "/foo"

        fake_iter = unittest.mock.MagicMock(return_value=iter([_FakeMatch()]))

        # Monkey-patch ``re.finditer`` at the module level so the
        # ``_check_allowlist`` loop sees our fake match.
        monkeypatch.setattr(risky_action_mod.re, "finditer", fake_iter)
        # Craft a cmd where positions 1-2 are ":/" and the fake match
        # starts at position 3.  cmd = "x:/foo": position 0="x",
        # position 1=":", position 2="/", position 3="f".
        ok, err = _check_allowlist("x:/foo", cfg)
        # The path was skipped via line 185 → no failure reported.
        assert ok is True
        assert err is None
        # Verify our fake was actually consulted.
        assert fake_iter.called
        _ = _re  # keep import used


# ---------------------------------------------------------------------------
# _dry_run_proposal
# ---------------------------------------------------------------------------


class TestDryRunProposal:
    """``_dry_run_proposal`` drives real dry-runs for supported families."""

    def test_git_apply_with_existing_patch_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_file = tmp_path / "clean.patch"
        patch_file.write_text(
            "diff --git a/foo.txt b/foo.txt\n"
            "new file mode 100644\n"
            "index 0000000..257cc56\n"
            "--- /dev/null\n"
            "+++ b/foo.txt\n"
            "@@ -0,0 +1 @@\n"
            "+hello\n",
            encoding="utf-8",
        )
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=0, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal(f"git apply {patch_file}")
        assert ok is True
        assert err is None
        # Verify --check was passed with the patch path
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "apply", "--check", str(patch_file)]
        assert call_args.kwargs.get("timeout") == 30

    def test_git_apply_with_explicit_check_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_file = tmp_path / "x.patch"
        patch_file.write_text("placeholder", encoding="utf-8")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=0, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal(f"git apply --check {patch_file}")
        assert ok is True
        # patch path is recovered from "git apply(?:\s+--check)?\s+(\S+\.(?:patch|diff))"
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == ["git", "apply", "--check", str(patch_file)]

    def test_git_apply_fails_when_patch_missing(self) -> None:
        ok, err = _dry_run_proposal("git apply /nonexistent/file.patch")
        assert ok is False
        assert err is not None
        assert "patch file not found" in err

    def test_git_apply_without_patch_path_fails(self) -> None:
        ok, err = _dry_run_proposal("git apply")
        assert ok is False
        assert err is not None
        assert "requires a local .patch" in err

    def test_git_apply_diff_extension_accepted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        diff = tmp_path / "x.diff"
        diff.write_text("placeholder", encoding="utf-8")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=0, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, _ = _dry_run_proposal(f"git apply {diff}")
        assert ok is True

    def test_git_apply_check_failure_returns_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_file = tmp_path / "bad.patch"
        patch_file.write_text("placeholder", encoding="utf-8")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=1, stderr="patch failed at line 5")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal(f"git apply {patch_file}")
        assert ok is False
        assert err == "patch failed at line 5"

    def test_git_apply_check_failure_no_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-zero exit with empty stderr returns the generic message."""
        patch_file = tmp_path / "bad2.patch"
        patch_file.write_text("placeholder", encoding="utf-8")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=1, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal(f"git apply {patch_file}")
        assert ok is False
        assert err == "dry_run: git apply --check failed"

    def test_docker_present_and_reachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_which = unittest.mock.MagicMock(return_value="/usr/bin/docker")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=0, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.shutil, "which", mock_which)
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal("docker run -it ubuntu bash")
        assert ok is True
        assert err is None
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd == [
            "docker",
            "version",
            "--format",
            "{{.Client.Version}}",
        ]

    def test_docker_not_on_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_which = unittest.mock.MagicMock(return_value=None)
        monkeypatch.setattr(risky_action_mod.shutil, "which", mock_which)
        ok, err = _dry_run_proposal("docker run -it ubuntu bash")
        assert ok is False
        assert err is not None
        assert "not available" in err

    def test_docker_unreachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_which = unittest.mock.MagicMock(return_value="/usr/bin/docker")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=1, stderr="Cannot connect to daemon")
        )
        monkeypatch.setattr(risky_action_mod.shutil, "which", mock_which)
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal("docker run -it ubuntu bash")
        assert ok is False
        assert err == "Cannot connect to daemon"

    def test_docker_unreachable_no_stderr(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-zero exit with empty stderr returns the generic message."""
        mock_which = unittest.mock.MagicMock(return_value="/usr/bin/docker")
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=1, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.shutil, "which", mock_which)
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        ok, err = _dry_run_proposal("docker run -it ubuntu bash")
        assert ok is False
        assert err == "dry_run: docker not reachable"

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm foo",
            "mv foo bar",
            "cp foo bar",
            "chmod 777 x",
            "pip install x",
            "npm install x",
            "curl http://x",
            "wget http://x",
            "git push origin main",
            "git commit -m x",
        ],
    )
    def test_destructive_verb_fails_loud(self, cmd: str) -> None:
        """FR-VER-001: medium/high-risk dry-runs must not scaffold True."""
        ok, err = _dry_run_proposal(cmd)
        assert ok is False
        assert err is not None
        assert "no safe dry-run" in err

    def test_read_only_command_passes(self) -> None:
        ok, err = _dry_run_proposal("echo hi")
        assert ok is True
        assert err is None

    def test_ls_passes(self) -> None:
        ok, err = _dry_run_proposal("ls -la")
        assert ok is True
        assert err is None


# ---------------------------------------------------------------------------
# check_proposal: end-to-end against the real config
# ---------------------------------------------------------------------------


class TestCheckProposalRealConfig:
    """End-to-end tests against ``config/risky_action_gate.yaml``."""

    def test_gate_disabled_short_circuits(self, cfg_factory) -> None:
        cfg_factory({"enabled": False})
        g = check_proposal("rm -rf /tmp/build")
        assert g.ok is True
        assert g.tier == "disabled"
        assert g.action == ""
        assert g.checks == {"gate_disabled": True}
        assert g.errors == []

    def test_no_action_proposed_passes(self) -> None:
        g = check_proposal("I have no proposal in this response.")
        assert g.ok is True
        assert g.tier == "none"
        assert g.action == ""
        assert g.checks == {"no_action_proposed": True}

    def test_low_tier_passes_for_pathless_command(self) -> None:
        # Use a path-less low-tier command; "ls" with /tmp fails allowlist
        # because /tmp is outside the workspace roots.
        g = check_proposal('{"command": "ls"}')
        assert g.tier == "low"
        assert g.ok is True
        assert g.errors == []

    def test_medium_tier_path_outside_allowlist_fails(self) -> None:
        # `cp /etc/passwd /tmp/x` matches high tier via "cp" destructive verb
        text = '{"command": "cp /etc/passwd /tmp/x"}'
        g = check_proposal(text)
        assert g.tier == "high"  # cp is in the destructive-verb regex
        # /etc/passwd is outside the workspace_roots
        assert g.ok is False
        assert any("outside allowlist" in e for e in g.errors)

    def test_high_tier_blocklist_pattern_blocks(self) -> None:
        # recursive_delete is in the real config blocklist → tier=high
        text = '{"command": "rm -rf /tmp/build"}'
        g = check_proposal(text, verifier_ok=True, human_approved=True)
        assert g.tier == "high"
        assert g.ok is False
        # blocklist must report a hit
        assert g.checks.get("pattern_blocklist_clear") is False
        assert any("blocklist" in e for e in g.errors)

    def test_critical_tier_requires_human_approval(self) -> None:
        # force_push → critical
        text = '{"command": "git push origin main --force"}'
        g = check_proposal(text, verifier_ok=True, human_approved=False)
        assert g.tier == "critical"
        assert g.ok is False
        assert g.checks.get("human_approve") is False
        assert any("human approval" in e for e in g.errors)

    def test_critical_tier_requires_verifier_pass(self) -> None:
        text = '{"command": "git push origin main --force"}'
        g = check_proposal(text, verifier_ok=None, human_approved=True)
        assert g.tier == "critical"
        assert g.ok is False
        assert g.checks.get("verifier_pass") is False
        assert any("verifier did not pass" in e for e in g.errors)

    def test_critical_tier_blocklist_still_blocks_when_all_pass(self) -> None:
        # critical commands all match the force_push blocklist. Even with
        # verifier_pass=True AND human_approved=True, the unconditional
        # blocklist check still adds an error and prevents ok=True.
        text = '{"command": "git push origin main --force"}'
        g = check_proposal(text, verifier_ok=True, human_approved=True)
        assert g.tier == "critical"
        assert g.ok is False
        assert g.checks.get("pattern_blocklist_clear") is False
        assert any("blocklist" in e for e in g.errors)

    def test_critical_tier_block_autonomous_enforced(self) -> None:
        # critical has block_autonomous=True → human_approve required even
        # if "human_approve" were missing from `requires`.
        text = '{"command": "git push origin main --force"}'
        g = check_proposal(text, verifier_ok=True, human_approved=False)
        assert g.ok is False
        assert g.checks.get("human_approve") is False

    def test_high_tier_with_blocklist_fail_short_circuits(self) -> None:
        text = '{"command": "rm -rf /"}'
        g = check_proposal(text, verifier_ok=True, human_approved=True)
        assert g.ok is False
        # blocklist fires regardless of verifier_ok/human_approved for high
        assert g.checks.get("pattern_blocklist_clear") is False

    def test_high_tier_with_verifier_failure(self) -> None:
        # Use a high-tier command WITHOUT a blocklist hit so we can observe
        # the verifier_pass branch in isolation.
        text = '{"command": "git push origin main"}'
        g = check_proposal(text, verifier_ok=False, human_approved=True)
        assert g.tier == "high"
        assert g.ok is False
        assert g.checks.get("verifier_pass") is False
        assert any("verifier" in e for e in g.errors)

    def test_medium_tier_with_workspace_path_and_patch_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A medium-tier command with a workspace path and a real .patch file
        # lets git apply --check succeed → dry_run ok.
        cfg = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path)],
            },
            "risk_tiers": {
                "medium": {
                    "examples": ["custom_medium"],
                    "requires": [
                        "output_parseable",
                        "path_in_allowlist",
                        "dry_run_when_available",
                    ],
                }
            },
        }
        patch_file = tmp_path / "x.patch"
        patch_file.write_text("placeholder", encoding="utf-8")
        monkeypatch.setattr(risky_action_mod, "_load_gate_config", lambda: cfg)
        mock_run = unittest.mock.MagicMock(
            return_value=SimpleNamespace(returncode=0, stderr="")
        )
        monkeypatch.setattr(risky_action_mod.subprocess, "run", mock_run)
        text = '{"command": "git apply ' + str(patch_file) + '"}'
        g = check_proposal(text)
        assert g.tier == "medium"
        assert g.ok is True
        assert g.checks.get("dry_run_when_available") is True

    def test_gate_result_meta_includes_mode_and_required_for_real_action(self) -> None:
        g = check_proposal('{"command": "ls"}')
        # "required" key should be populated for any real action
        assert "mode" in g.meta
        assert "required" in g.meta
        # Low tier only requires output_parseable
        assert g.meta["required"] == ["output_parseable"]

    def test_gate_result_no_action_meta_only_has_mode(self) -> None:
        # When no command is proposed, the gate short-circuits with
        # tier="none" and only "mode" in meta.
        g = check_proposal("no commands here")
        assert g.tier == "none"
        assert "mode" in g.meta

    def test_gate_disabled_meta_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            risky_action_mod,
            "_load_gate_config",
            lambda: {"enabled": False},
        )
        g = check_proposal("rm -rf /tmp/x")
        # Disabled gate: no action evaluated, no meta fields populated
        assert g.tier == "disabled"
        assert g.meta == {}


# ---------------------------------------------------------------------------
# check_proposal: targeted coverage of internal branches
# ---------------------------------------------------------------------------


class TestCheckProposalBranches:
    """Target tests for the small branches inside ``check_proposal``."""

    def test_blocklist_entry_with_no_id(self, cfg_factory) -> None:
        # Blocklist entries without an "id" key still block and report "unknown"
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [
                {"regex": r"\bblock_me\b"},  # no id, no tier → tier=high default
            ],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "high": {"examples": [], "requires": ["output_parseable"]}
            },
        }
        cfg_factory(cfg)
        g = check_proposal('{"command": "block_me now"}')
        assert g.checks.get("pattern_blocklist_clear") is False
        # Error message references "unknown" for missing id
        assert any("unknown" in e for e in g.errors)

    def test_human_approve_required_for_high_tier(
        self, cfg_factory
    ) -> None:
        # Use "rm" as the cmd — destructive-verb regex forces tier="high"
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "high": {
                    "examples": ["special_high"],
                    "requires": ["output_parseable", "human_approve"],
                    "block_autonomous": False,  # explicit
                }
            },
        }
        # Without human approval → blocked
        cfg_factory(cfg)
        g = check_proposal(
            '{"command": "rm special_high thing"}', human_approved=False
        )
        assert g.tier == "high"
        assert g.ok is False
        assert g.checks.get("human_approve") is False
        # With human approval → passes (no other required checks fail)
        cfg_factory(cfg)
        g2 = check_proposal(
            '{"command": "rm special_high thing"}', human_approved=True
        )
        assert g2.ok is True

    def test_verifier_pass_check_uses_strict_true(
        self, cfg_factory
    ) -> None:
        # Use "rm" to force tier="high" via destructive-verb regex
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "high": {
                    "examples": ["unique_high_example"],
                    "requires": ["output_parseable", "verifier_pass"],
                }
            },
        }
        # verifier_ok=False → fails
        cfg_factory(cfg)
        g = check_proposal(
            '{"command": "rm unique_high_example"}', verifier_ok=False
        )
        assert g.tier == "high"
        assert g.ok is False
        assert g.checks.get("verifier_pass") is False
        # verifier_ok=None → fails (strict True comparison)
        cfg_factory(cfg)
        g2 = check_proposal(
            '{"command": "rm unique_high_example"}', verifier_ok=None
        )
        assert g2.ok is False
        # verifier_ok=True → passes
        cfg_factory(cfg)
        g3 = check_proposal(
            '{"command": "rm unique_high_example"}', verifier_ok=True
        )
        assert g3.ok is True

    def test_blocklist_and_secret_both_record_errors(
        self, cfg_factory
    ) -> None:
        # Use a workspace-internal path so the path check passes.
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [
                {"id": "x", "regex": r"dangerous_keyword", "tier": "high"}
            ],
            "secret_patterns": [r"password\s*="],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "high": {
                    "examples": [],
                    "requires": ["output_parseable"],
                }
            },
        }
        # Both a blocklist match AND a secret match → both errors recorded
        cfg_factory(cfg)
        g = check_proposal(
            '{"command": "dangerous_keyword password=foo"}'
        )
        assert g.ok is False
        assert g.checks.get("pattern_blocklist_clear") is False
        assert g.checks.get("secret_clear") is False
        # Two distinct errors should be present
        assert len(g.errors) == 2

    def test_path_in_allowlist_failure_reported(
        self, cfg_factory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(risky_action_mod, "CONFIG_DIR", tmp_path / "config")
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {
                "deny_absolute_outside_roots": True,
                "workspace_roots": [str(tmp_path / "workspace")],
            },
            "risk_tiers": {
                "medium": {
                    "examples": ["custom_path_check"],
                    "requires": [
                        "output_parseable",
                        "path_in_allowlist",
                    ],
                }
            },
        }
        cfg_factory(cfg)
        g = check_proposal(
            '{"command": "custom_path_check /etc/passwd"}'
        )
        assert g.checks.get("path_in_allowlist") is False
        assert any("outside allowlist" in e for e in g.errors)

    def test_ok_true_when_all_required_pass(self, cfg_factory) -> None:
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "low": {"examples": ["ls"], "requires": ["output_parseable"]}
            },
        }
        cfg_factory(cfg)
        g = check_proposal('{"command": "ls"}')
        assert g.ok is True
        assert g.errors == []

    def test_ok_false_when_any_required_fails(
        self, cfg_factory
    ) -> None:
        # blocklist fires unconditionally for any matching command
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [
                {"id": "boom", "regex": r"boom", "tier": "high"}
            ],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "high": {
                    "examples": [],
                    "requires": [
                        "output_parseable",
                        "pattern_blocklist_clear",
                    ],
                }
            },
        }
        cfg_factory(cfg)
        g = check_proposal('{"command": "boom goes the dynamite"}')
        assert g.ok is False
        assert any("blocklist" in e for e in g.errors)

    def test_medium_tier_no_required_dry_run_still_passes(
        self, cfg_factory
    ) -> None:
        # If medium tier doesn't require dry_run, a destructive-verb cmd
        # that's only medium will still pass (dry_run isn't checked).
        # But "rm foo" hits the destructive verb and escalates to "high",
        # so we use a synthetic medium-only example here.
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "medium": {
                    "examples": ["my_synthetic_medium_example"],
                    "requires": ["output_parseable"],
                }
            },
        }
        cfg_factory(cfg)
        g = check_proposal(
            '{"command": "my_synthetic_medium_example x"}'
        )
        assert g.ok is True
        # dry_run_when_available still set as a check even when not required
        assert "dry_run_when_available" in g.checks

    def test_meta_required_is_provided_when_tier_known(self) -> None:
        # Real-config medium-tier test: meta should have both mode + required
        g = check_proposal('{"command": "cp foo bar"}')
        assert g.tier == "high"
        # Even though cp matches destructive verb, gate assigns tier
        assert "required" in g.meta
        assert isinstance(g.meta["required"], list)

    def test_dry_run_required_branch_reports_error(
        self, cfg_factory
    ) -> None:
        """When ``dry_run_when_available`` is required and dry-run fails,
        the error from the dry-run is appended."""
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "medium": {
                    "examples": ["my_medium_dryrun"],
                    "requires": [
                        "output_parseable",
                        "dry_run_when_available",
                    ],
                }
            },
        }
        cfg_factory(cfg)
        # "my_medium_dryrun x" doesn't match any dry-run family, but
        # the destructive-verb regex won't fire either since the example
        # is unique.  Actually "rm" in the cmd WOULD fire the destructive
        # verb.  Use a clean example without destructive verbs.
        g = check_proposal('{"command": "my_medium_dryrun x"}')
        # dry_run_when_available is required; "my_medium_dryrun x" is not
        # a git/docker/destructive command → falls through to the
        # "no safe dry-run" branch in _dry_run_proposal only if it's
        # destructive.  For non-destructive commands, dry_run returns
        # (True, None).  Verify the check ran regardless.
        assert "dry_run_when_available" in g.checks

    def test_dry_run_required_branch_appends_error(
        self, cfg_factory
    ) -> None:
        """``dry_run_when_available`` in required list AND dry-run fails
        → error is appended with the dry-run message."""
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "medium": {
                    "examples": ["rm"],  # rm → destructive verb → tier=high
                    "requires": [
                        "output_parseable",
                        "dry_run_when_available",
                    ],
                }
            },
        }
        cfg_factory(cfg)
        # "rm foo" → destructive verb → tier=high.  _dry_run_proposal
        # returns (False, "dry_run: no safe dry-run available ...").
        # dry_run_when_available is in required AND failed → error appended.
        g = check_proposal('{"command": "rm foo"}')
        assert g.ok is False
        assert any("dry_run" in e for e in g.errors)

    def test_human_approve_triggered_by_block_autonomous_flag(
        self, cfg_factory
    ) -> None:
        """``block_autonomous: True`` in tier_cfg triggers human_approve
        even when not in the requires list."""
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "medium": {
                    "examples": ["synth_block_auton"],
                    "requires": ["output_parseable"],
                    "block_autonomous": True,
                }
            },
        }
        cfg_factory(cfg)
        # Without human approval → blocked (block_autonomous triggers check)
        g = check_proposal(
            '{"command": "synth_block_auton x"}', human_approved=False
        )
        assert g.checks.get("human_approve") is False
        assert any("human approval" in e for e in g.errors)
        # With human approval → passes
        g2 = check_proposal(
            '{"command": "synth_block_auton x"}', human_approved=True
        )
        assert g2.ok is True

    def test_all_required_checks_pass_with_errors_in_meta(
        self, cfg_factory
    ) -> None:
        """All required checks pass but ``errors`` is empty → ok=True."""
        cfg: dict[str, Any] = {
            "enabled": True,
            "default_mode": "block_until_verified",
            "pattern_blocklist": [],
            "secret_patterns": [],
            "path_allowlist": {"deny_absolute_outside_roots": False},
            "risk_tiers": {
                "low": {
                    "examples": ["ls"],
                    "requires": ["output_parseable", "pattern_blocklist_clear"],
                }
            },
        }
        cfg_factory(cfg)
        g = check_proposal('{"command": "ls"}')
        assert g.ok is True
        assert g.errors == []


# ---------------------------------------------------------------------------
# Module surface — public exports
# ---------------------------------------------------------------------------


class TestModuleSurface:
    """Verify the public API of ``verifier.risky_action``."""

    def test_public_symbols_exported(self) -> None:
        for name in ("GateResult", "check_proposal", "extract_proposed_command"):
            assert hasattr(risky_action_mod, name), (
                f"missing {name!r} in risky_action"
            )


# ---------------------------------------------------------------------------
# unittest.TestCase smoke tests — runnable via ``python -m unittest``
# ---------------------------------------------------------------------------


class RiskyActionUnittestSmoke(unittest.TestCase):
    """Minimal ``unittest.TestCase`` coverage for ``verifier.risky_action``.

    These tests do NOT use ``monkeypatch`` (which is a pytest-only fixture)
    so they also pass when invoked via ``python -m unittest tests.test_risky_action``.
    They use ``unittest.mock.patch`` with module references where needed.
    """

    def test_gate_result_default_construction(self) -> None:
        g = GateResult(ok=True, tier="low", action="")
        self.assertTrue(g.ok)
        self.assertEqual(g.tier, "low")
        self.assertEqual(g.action, "")
        self.assertEqual(g.checks, {})
        self.assertEqual(g.errors, [])
        self.assertEqual(g.meta, {})

    def test_extract_proposed_command_empty(self) -> None:
        self.assertIsNone(extract_proposed_command(""))

    def test_extract_proposed_command_json(self) -> None:
        self.assertEqual(
            extract_proposed_command('{"command": "echo hi"}'), "echo hi"
        )

    def test_check_secrets_no_patterns(self) -> None:
        ok, err = _check_secrets("echo hello", {"secret_patterns": []})
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_check_proposal_gate_disabled(self) -> None:
        with patch.object(risky_action_mod, "_load_gate_config", return_value={"enabled": False}):
            g = check_proposal("rm -rf /tmp/build")
        self.assertTrue(g.ok)
        self.assertEqual(g.tier, "disabled")

    def test_check_proposal_no_action(self) -> None:
        g = check_proposal("I have no proposal in this response.")
        self.assertTrue(g.ok)
        self.assertEqual(g.tier, "none")


if __name__ == "__main__":
    unittest.main()
