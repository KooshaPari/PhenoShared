"""Tests for thegent.integrations.rollout_scorecard — Enterprise rollout scorecard.

@trace WL-320
"""

from __future__ import annotations

import pytest

from thegent.integrations.rollout_scorecard import (
    RolloutScorecard,
    RolloutProfile,
    ScorecardCheck,
    load_rollout_profile,
    validate_rollout_profile,
)


class TestScorecardCheck:
    """Test ScorecardCheck dataclass. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_create_passed_check(self) -> None:
        """Can create a ScorecardCheck that passed."""
        check = ScorecardCheck(
            name="auth_scopes",
            passed=True,
            details="All scopes verified",
        )

        assert check.name == "auth_scopes"
        assert check.passed is True
        assert check.details == "All scopes verified"

    @pytest.mark.requirement("WL-320")
    def test_create_failed_check(self) -> None:
        """Can create a ScorecardCheck that failed."""
        check = ScorecardCheck(
            name="startup_validation",
            passed=False,
            details="Validation timeout",
        )

        assert check.name == "startup_validation"
        assert check.passed is False
        assert check.details == "Validation timeout"

    @pytest.mark.requirement("WL-320")
    def test_check_default_details(self) -> None:
        """ScorecardCheck defaults details to empty string."""
        check = ScorecardCheck(name="test_check", passed=True)
        assert check.details == ""


class TestRolloutScorecardInit:
    """Test RolloutScorecard initialization. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_init_creates_empty_scorecard(self) -> None:
        """Scorecard initializes empty."""
        scorecard = RolloutScorecard()
        assert scorecard.score() == 0.0
        assert scorecard.is_go() is False

    @pytest.mark.requirement("WL-320")
    def test_required_checks_are_defined(self) -> None:
        """REQUIRED_CHECKS contains 8 required check names."""
        assert len(RolloutScorecard.REQUIRED_CHECKS) == 8
        assert "auth_scopes" in RolloutScorecard.REQUIRED_CHECKS
        assert "startup_validation" in RolloutScorecard.REQUIRED_CHECKS
        assert "mapping_validated" in RolloutScorecard.REQUIRED_CHECKS
        assert "conflict_guardrails" in RolloutScorecard.REQUIRED_CHECKS
        assert "rate_limit_configured" in RolloutScorecard.REQUIRED_CHECKS
        assert "rollback_snapshot" in RolloutScorecard.REQUIRED_CHECKS
        assert "compliance_snapshot" in RolloutScorecard.REQUIRED_CHECKS
        assert "drift_baseline" in RolloutScorecard.REQUIRED_CHECKS


class TestRolloutScorecardAddCheck:
    """Test RolloutScorecard.add_check() method. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_add_single_check_passed(self) -> None:
        """Can add a single passing check."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True, "Verified")

        assert scorecard.score() == 1 / 8  # 1 of 8 checks passed

    @pytest.mark.requirement("WL-320")
    def test_add_single_check_failed(self) -> None:
        """Can add a single failing check."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", False, "Failed verification")

        assert scorecard.score() == 0.0  # 0 of 8 checks passed

    @pytest.mark.requirement("WL-320")
    def test_add_check_without_details(self) -> None:
        """Can add check without details."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)

        summary = scorecard.summary()
        check = next(c for c in summary["checks"] if c["name"] == "auth_scopes")
        assert check["details"] == ""

    @pytest.mark.requirement("WL-320")
    def test_add_multiple_checks(self) -> None:
        """Can add multiple checks."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)
        scorecard.add_check("startup_validation", True)
        scorecard.add_check("mapping_validated", False)

        assert scorecard.score() == 2 / 8  # 2 of 8 checks passed

    @pytest.mark.requirement("WL-320")
    def test_add_check_overwrites_previous(self) -> None:
        """Adding a check with same name overwrites previous."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)
        scorecard.add_check("auth_scopes", False, "Re-verification failed")

        # Only the second check should count
        summary = scorecard.summary()
        check = next(c for c in summary["checks"] if c["name"] == "auth_scopes")
        assert check["passed"] is False
        assert check["details"] == "Re-verification failed"


class TestRolloutScorecardScore:
    """Test RolloutScorecard.score() method. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_score_all_failed(self) -> None:
        """Score is 0.0 when all checks fail."""
        scorecard = RolloutScorecard()
        for check_name in RolloutScorecard.REQUIRED_CHECKS:
            scorecard.add_check(check_name, False)

        assert scorecard.score() == 0.0

    @pytest.mark.requirement("WL-320")
    def test_score_all_passed(self) -> None:
        """Score is 1.0 when all checks pass."""
        scorecard = RolloutScorecard()
        for check_name in RolloutScorecard.REQUIRED_CHECKS:
            scorecard.add_check(check_name, True)

        assert scorecard.score() == 1.0

    @pytest.mark.requirement("WL-320")
    def test_score_partial(self) -> None:
        """Score reflects fraction of checks passed."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)
        scorecard.add_check("startup_validation", True)
        scorecard.add_check("mapping_validated", True)
        scorecard.add_check("conflict_guardrails", True)

        assert scorecard.score() == 0.5  # 4 of 8 checks

    @pytest.mark.requirement("WL-320")
    def test_score_missing_checks_count_as_failed(self) -> None:
        """Score counts missing checks as failed."""
        scorecard = RolloutScorecard()
        # Add only 2 checks
        scorecard.add_check("auth_scopes", True)
        scorecard.add_check("startup_validation", True)

        # 2 out of 8 passed (remaining 6 are not added, count as failed)
        assert scorecard.score() == 2 / 8


class TestRolloutScorecardIsGo:
    """Test RolloutScorecard.is_go() method. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_is_go_false_when_empty(self) -> None:
        """is_go() is False for empty scorecard."""
        scorecard = RolloutScorecard()
        assert scorecard.is_go() is False

    @pytest.mark.requirement("WL-320")
    def test_is_go_false_when_partial(self) -> None:
        """is_go() is False when only some checks pass."""
        scorecard = RolloutScorecard()
        for check_name in RolloutScorecard.REQUIRED_CHECKS[:4]:
            scorecard.add_check(check_name, True)

        assert scorecard.is_go() is False

    @pytest.mark.requirement("WL-320")
    def test_is_go_true_when_all_pass(self) -> None:
        """is_go() is True when all checks pass."""
        scorecard = RolloutScorecard()
        for check_name in RolloutScorecard.REQUIRED_CHECKS:
            scorecard.add_check(check_name, True)

        assert scorecard.is_go() is True

    @pytest.mark.requirement("WL-320")
    def test_is_go_false_when_one_fails(self) -> None:
        """is_go() is False even if only one check fails."""
        scorecard = RolloutScorecard()
        for i, check_name in enumerate(RolloutScorecard.REQUIRED_CHECKS):
            scorecard.add_check(check_name, i != 0)  # First check fails

        assert scorecard.is_go() is False


class TestRolloutScorecardSummary:
    """Test RolloutScorecard.summary() method. @trace WL-320"""

    @pytest.mark.requirement("WL-320")
    def test_summary_structure(self) -> None:
        """Summary has expected structure."""
        scorecard = RolloutScorecard()
        summary = scorecard.summary()

        assert "score" in summary
        assert "go" in summary
        assert "checks" in summary
        assert isinstance(summary["score"], float)
        assert isinstance(summary["go"], bool)
        assert isinstance(summary["checks"], list)

    @pytest.mark.requirement("WL-320")
    def test_summary_includes_all_required_checks(self) -> None:
        """Summary includes all 8 required checks."""
        scorecard = RolloutScorecard()
        summary = scorecard.summary()

        check_names = {c["name"] for c in summary["checks"]}
        assert check_names == set(RolloutScorecard.REQUIRED_CHECKS)

    @pytest.mark.requirement("WL-320")
    def test_summary_missing_checks_show_as_failed(self) -> None:
        """Summary shows unadded checks as failed."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)

        summary = scorecard.summary()

        # auth_scopes should be passed
        auth_check = next(c for c in summary["checks"] if c["name"] == "auth_scopes")
        assert auth_check["passed"] is True

        # Other checks should be failed (not added)
        startup_check = next(c for c in summary["checks"] if c["name"] == "startup_validation")
        assert startup_check["passed"] is False

    @pytest.mark.requirement("WL-320")
    def test_summary_score_matches_is_go(self) -> None:
        """Summary's go flag matches is_go() result."""
        scorecard = RolloutScorecard()
        for check_name in RolloutScorecard.REQUIRED_CHECKS:
            scorecard.add_check(check_name, True)

        summary = scorecard.summary()

        assert summary["go"] == scorecard.is_go()
        assert summary["score"] == scorecard.score()

    @pytest.mark.requirement("WL-320")
    def test_summary_includes_details(self) -> None:
        """Summary includes check details."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True, "All OAuth scopes granted")
        scorecard.add_check("startup_validation", False, "Timeout after 30s")

        summary = scorecard.summary()

        auth_check = next(c for c in summary["checks"] if c["name"] == "auth_scopes")
        assert auth_check["details"] == "All OAuth scopes granted"

        startup_check = next(c for c in summary["checks"] if c["name"] == "startup_validation")
        assert startup_check["details"] == "Timeout after 30s"

    @pytest.mark.requirement("WL-320")
    def test_summary_empty_details_default(self) -> None:
        """Summary shows empty string for checks without details."""
        scorecard = RolloutScorecard()
        scorecard.add_check("auth_scopes", True)  # No details

        summary = scorecard.summary()

        auth_check = next(c for c in summary["checks"] if c["name"] == "auth_scopes")
        assert auth_check["details"] == ""


@pytest.mark.requirement("WL-239")
class TestStagedRolloutProfiles:
    """Tests for WL-239 staged rollout profiles."""

    @pytest.mark.requirement("WL-320")
    def test_load_dev_staging_prod_profiles(self) -> None:
        dev = load_rollout_profile("dev")
        staging = load_rollout_profile("staging")
        prod = load_rollout_profile("prod")
        assert dev.name == "dev"
        assert staging.name == "staging"
        assert prod.name == "prod"
        assert dev.max_failure_rate > prod.max_failure_rate

    @pytest.mark.requirement("WL-320")
    def test_profile_loader_rejects_unknown_profile(self) -> None:
        with pytest.raises(ValueError, match="Unsupported rollout profile"):
            load_rollout_profile("qa")

    @pytest.mark.requirement("WL-320")
    def test_validate_profile_requires_prod_safety_defaults(self) -> None:
        unsafe = RolloutProfile(
            name="prod",
            max_failure_rate=0.05,
            max_p95_latency_ms=1000.0,
            require_manual_approval=True,
            auto_rollback_enabled=False,
        )
        with pytest.raises(ValueError, match="must enable auto_rollback"):
            validate_rollout_profile(unsafe)
